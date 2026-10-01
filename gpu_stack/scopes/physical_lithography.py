"""
scopes/physical_lithography.py
==============================

How the chip is made, in one short chapter. A lithography tool prints the
smallest feature it can resolve, and the Rayleigh relation gives that size:

    critical dimension = k1 * wavelength / NA

Wavelength and numerical aperture (NA) are plain inputs here: 13.5 nm for
EUV, 193 nm for ArF immersion (see `gpu_stack.presets.lithography`). k1 is
the process factor. It is composed from four dimensionless factors: image
contrast and resolution-enhancement tricks push it down, while resist
latitude and mask-error amplification push it up. The printed gate, contact,
metal-width, and metal-spacing sizes feed the process scope (physical_process),
which turns them into transistor and wire geometry.
"""

import sympy as sp

from ..core import Approximation, Inequality, Reference, gt, valid_all, var
from ..core.units import METER


LITHOGRAPHY_REF = Reference(
    citation="Rayleigh resolution relation CD = k1 * lambda / NA; k1 as a process factor combining image contrast, resist latitude, mask-error amplification, and resolution enhancement",
    kind="memo",
)


# ----- exposure inputs -----------------------------------------------------

lithography_wavelength = var(
    "physical.lithography.wavelength", "lambda_litho", "m",
    "Exposure wavelength of the lithography tool (13.5 nm for EUV, 193 nm for ArF immersion).",
    scope="physical",
    positive=True,
    sp_units=METER,
    references=[LITHOGRAPHY_REF],
)
lithography_numerical_aperture = var(
    "physical.lithography.numerical_aperture", "NA_litho", "dimensionless",
    "Numerical aperture of the lithography lens: how wide a cone of light it collects.",
    scope="physical",
    positive=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_REF],
)
lithography_medium_refractive_index = var(
    "physical.lithography.medium_refractive_index", "n_litho_med", "dimensionless",
    "Refractive index of the medium between the last lens and the wafer (1 in vacuum or air, about 1.44 for water at 193 nm).",
    scope="physical",
    positive=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_REF],
)


# ----- k1 process factor ----------------------------------------------------

gate_resolution_k1 = var(
    "physical.lithography.gate_k1",
    "k1_gate_litho",
    "dimensionless",
    "Effective k1 factor for gate critical-dimension patterning.",
    scope="physical",
    positive=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_REF],
)
contact_resolution_k1 = var(
    "physical.lithography.contact_k1",
    "k1_contact_litho",
    "dimensionless",
    "Effective k1 factor for source/drain contact critical-dimension patterning.",
    scope="physical",
    positive=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_REF],
)
metal_width_resolution_k1 = var(
    "physical.lithography.metal_width_k1",
    "k1_metal_w_litho",
    "dimensionless",
    "Effective k1 factor for minimum metal width patterning.",
    scope="physical",
    positive=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_REF],
)
metal_spacing_resolution_k1 = var(
    "physical.lithography.metal_spacing_k1",
    "k1_metal_s_litho",
    "dimensionless",
    "Effective k1 factor for minimum metal spacing patterning.",
    scope="physical",
    positive=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_REF],
)
lithography_gate_k1_aerial_image_contrast_factor = var(
    "physical.lithography.gate_k1_aerial_image_contrast_factor",
    "chi_img_gate_litho",
    "dimensionless",
    "Dimensionless aerial-image contrast factor reducing the gate k1 process factor.",
    scope="physical",
    positive=True,
    value_range=(0.0, 1.0),
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_REF],
)
lithography_gate_k1_resist_process_factor = var(
    "physical.lithography.gate_k1_resist_process_factor",
    "chi_resist_gate_litho",
    "dimensionless",
    "Dimensionless resist and process-latitude factor increasing the gate k1 requirement.",
    scope="physical",
    positive=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_REF],
)
lithography_gate_k1_mask_error_factor = var(
    "physical.lithography.gate_k1_mask_error_factor",
    "chi_mask_gate_litho",
    "dimensionless",
    "Dimensionless mask-error and pattern-transfer amplification factor for gate k1.",
    scope="physical",
    positive=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_REF],
)
lithography_gate_k1_resolution_enhancement_factor = var(
    "physical.lithography.gate_k1_resolution_enhancement_factor",
    "eta_RET_gate_litho",
    "dimensionless",
    "Dimensionless resolution-enhancement factor reducing the effective gate k1.",
    scope="physical",
    positive=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_REF],
)


# ----- printed critical dimensions -----------------------------------------

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


eq_lithography_gate_k1_from_process_factors = Approximation(
    "physical.eq.lithography_gate_k1_from_process_factors",
    gate_resolution_k1.symbol,
    (
        lithography_gate_k1_resist_process_factor.symbol
        * lithography_gate_k1_mask_error_factor.symbol
        / (
            lithography_gate_k1_aerial_image_contrast_factor.symbol
            * lithography_gate_k1_resolution_enhancement_factor.symbol
        )
    ),
    valid_all(
        gt(lithography_gate_k1_aerial_image_contrast_factor.symbol, 0),
        gt(lithography_gate_k1_resist_process_factor.symbol, 0),
        gt(lithography_gate_k1_mask_error_factor.symbol, 0),
        gt(lithography_gate_k1_resolution_enhancement_factor.symbol, 0),
    ),
    "Gate k1 from process latitude and mask-error factors divided by imaging contrast and resolution enhancement.",
    references=[LITHOGRAPHY_REF],
    check_units=True,
)
eq_contact_resolution_k1_from_gate_baseline = Approximation(
    "physical.eq.contact_k1_from_gate_baseline",
    contact_resolution_k1.symbol,
    gate_resolution_k1.symbol,
    gt(gate_resolution_k1.symbol, 0),
    "Contact k1 approximated from the shared Rayleigh/process-family gate k1 baseline.",
    references=[LITHOGRAPHY_REF],
    check_units=True,
)
eq_metal_width_resolution_k1_from_gate_baseline = Approximation(
    "physical.eq.metal_width_k1_from_gate_baseline",
    metal_width_resolution_k1.symbol,
    gate_resolution_k1.symbol,
    gt(gate_resolution_k1.symbol, 0),
    "Minimum-metal-width k1 approximated from the shared Rayleigh/process-family gate k1 baseline.",
    references=[LITHOGRAPHY_REF],
    check_units=True,
)
eq_metal_spacing_resolution_k1_from_gate_baseline = Approximation(
    "physical.eq.metal_spacing_k1_from_gate_baseline",
    metal_spacing_resolution_k1.symbol,
    gate_resolution_k1.symbol,
    gt(gate_resolution_k1.symbol, 0),
    "Minimum-metal-spacing k1 approximated from the shared Rayleigh/process-family gate k1 baseline.",
    references=[LITHOGRAPHY_REF],
    check_units=True,
)

ineq_lithography_numerical_aperture_within_medium_index = Inequality(
    "physical.ineq.lithography_numerical_aperture_within_medium_index",
    lithography_numerical_aperture.symbol, lithography_medium_refractive_index.symbol, "<=",
    "Lithography numerical aperture cannot exceed the imaging-medium refractive index.",
    references=[LITHOGRAPHY_REF], check_units=True,
)


def _rayleigh(name, out, k1, description):
    return Approximation(
        name,
        out.symbol,
        k1.symbol * lithography_wavelength.symbol / lithography_numerical_aperture.symbol,
        valid_all(
            gt(k1.symbol, 0),
            gt(lithography_wavelength.symbol, 0),
            gt(lithography_numerical_aperture.symbol, 0),
        ),
        description,
        references=[LITHOGRAPHY_REF],
        check_units=True,
    )


eq_gate_lithography_resolution = _rayleigh(
    "physical.eq.gate_lithography_resolution",
    gate_lithography_resolution,
    gate_resolution_k1,
    "Gate critical-dimension resolution from Rayleigh-style k1 wavelength over numerical aperture.",
)
eq_contact_lithography_resolution = _rayleigh(
    "physical.eq.contact_lithography_resolution",
    contact_lithography_resolution,
    contact_resolution_k1,
    "Contact critical-dimension resolution from Rayleigh-style k1 wavelength over numerical aperture.",
)
eq_metal_width_lithography_resolution = _rayleigh(
    "physical.eq.metal_width_lithography_resolution",
    metal_width_lithography_resolution,
    metal_width_resolution_k1,
    "Minimum-metal-width resolution from Rayleigh-style k1 wavelength over numerical aperture.",
)
eq_metal_spacing_lithography_resolution = _rayleigh(
    "physical.eq.metal_spacing_lithography_resolution",
    metal_spacing_lithography_resolution,
    metal_spacing_resolution_k1,
    "Minimum-metal-spacing resolution from Rayleigh-style k1 wavelength over numerical aperture.",
)


LITHOGRAPHY_VARIABLES = [
    lithography_wavelength,
    lithography_numerical_aperture,
    lithography_medium_refractive_index,
    gate_resolution_k1,
    contact_resolution_k1,
    metal_width_resolution_k1,
    metal_spacing_resolution_k1,
    lithography_gate_k1_aerial_image_contrast_factor,
    lithography_gate_k1_resist_process_factor,
    lithography_gate_k1_mask_error_factor,
    lithography_gate_k1_resolution_enhancement_factor,
    gate_lithography_resolution,
    contact_lithography_resolution,
    metal_width_lithography_resolution,
    metal_spacing_lithography_resolution,
]

LITHOGRAPHY_EQUATIONS = [
    eq_lithography_gate_k1_from_process_factors,
    eq_contact_resolution_k1_from_gate_baseline,
    eq_metal_width_resolution_k1_from_gate_baseline,
    eq_metal_spacing_resolution_k1_from_gate_baseline,
    ineq_lithography_numerical_aperture_within_medium_index,
    eq_gate_lithography_resolution,
    eq_contact_lithography_resolution,
    eq_metal_width_lithography_resolution,
    eq_metal_spacing_lithography_resolution,
]

__all__ = [
    "LITHOGRAPHY_REF",
    "LITHOGRAPHY_VARIABLES",
    "LITHOGRAPHY_EQUATIONS",
    "lithography_wavelength",
    "lithography_numerical_aperture",
    "lithography_medium_refractive_index",
    "gate_resolution_k1",
    "contact_resolution_k1",
    "metal_width_resolution_k1",
    "metal_spacing_resolution_k1",
    "lithography_gate_k1_aerial_image_contrast_factor",
    "lithography_gate_k1_resist_process_factor",
    "lithography_gate_k1_mask_error_factor",
    "lithography_gate_k1_resolution_enhancement_factor",
    "gate_lithography_resolution",
    "contact_lithography_resolution",
    "metal_width_lithography_resolution",
    "metal_spacing_lithography_resolution",
    "eq_lithography_gate_k1_from_process_factors",
    "eq_contact_resolution_k1_from_gate_baseline",
    "eq_metal_width_resolution_k1_from_gate_baseline",
    "eq_metal_spacing_resolution_k1_from_gate_baseline",
    "ineq_lithography_numerical_aperture_within_medium_index",
    "eq_gate_lithography_resolution",
    "eq_contact_lithography_resolution",
    "eq_metal_width_lithography_resolution",
    "eq_metal_spacing_lithography_resolution",
]
