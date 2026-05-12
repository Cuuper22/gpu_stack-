"""
scopes/physical_lithography_k1.py
=================================

Feature-family k1 process-factor layer.
"""

import sympy as sp

from ..core import Approximation, Reference, gt, valid_all, var


LITHOGRAPHY_K1_REF = Reference(
    citation="Lithography k1 abstraction: effective Rayleigh process factor from aerial-image contrast, resist/process latitude, mask-error amplification, and resolution enhancement",
    kind="memo",
)


gate_resolution_k1 = var(
    "physical.lithography.gate_k1",
    "k1_gate_litho",
    "dimensionless",
    "Effective k1 factor for gate critical-dimension patterning.",
    scope="physical",
    positive=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_K1_REF],
)
contact_resolution_k1 = var(
    "physical.lithography.contact_k1",
    "k1_contact_litho",
    "dimensionless",
    "Effective k1 factor for source/drain contact critical-dimension patterning.",
    scope="physical",
    positive=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_K1_REF],
)
metal_width_resolution_k1 = var(
    "physical.lithography.metal_width_k1",
    "k1_metal_w_litho",
    "dimensionless",
    "Effective k1 factor for minimum metal width patterning.",
    scope="physical",
    positive=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_K1_REF],
)
metal_spacing_resolution_k1 = var(
    "physical.lithography.metal_spacing_k1",
    "k1_metal_s_litho",
    "dimensionless",
    "Effective k1 factor for minimum metal spacing patterning.",
    scope="physical",
    positive=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_K1_REF],
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
    references=[LITHOGRAPHY_K1_REF],
)
lithography_gate_k1_resist_process_factor = var(
    "physical.lithography.gate_k1_resist_process_factor",
    "chi_resist_gate_litho",
    "dimensionless",
    "Dimensionless resist and process-latitude factor increasing the gate k1 requirement.",
    scope="physical",
    positive=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_K1_REF],
)
lithography_gate_k1_mask_error_factor = var(
    "physical.lithography.gate_k1_mask_error_factor",
    "chi_mask_gate_litho",
    "dimensionless",
    "Dimensionless mask-error and pattern-transfer amplification factor for gate k1.",
    scope="physical",
    positive=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_K1_REF],
)
lithography_gate_k1_resolution_enhancement_factor = var(
    "physical.lithography.gate_k1_resolution_enhancement_factor",
    "eta_RET_gate_litho",
    "dimensionless",
    "Dimensionless resolution-enhancement factor reducing the effective gate k1.",
    scope="physical",
    positive=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_K1_REF],
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
    references=[LITHOGRAPHY_K1_REF],
    check_units=True,
)
eq_contact_resolution_k1_from_gate_baseline = Approximation(
    "physical.eq.contact_k1_from_gate_baseline",
    contact_resolution_k1.symbol,
    gate_resolution_k1.symbol,
    gt(gate_resolution_k1.symbol, 0),
    "Contact k1 approximated from the shared Rayleigh/process-family gate k1 baseline.",
    references=[LITHOGRAPHY_K1_REF],
    check_units=True,
)
eq_metal_width_resolution_k1_from_gate_baseline = Approximation(
    "physical.eq.metal_width_k1_from_gate_baseline",
    metal_width_resolution_k1.symbol,
    gate_resolution_k1.symbol,
    gt(gate_resolution_k1.symbol, 0),
    "Minimum-metal-width k1 approximated from the shared Rayleigh/process-family gate k1 baseline.",
    references=[LITHOGRAPHY_K1_REF],
    check_units=True,
)
eq_metal_spacing_resolution_k1_from_gate_baseline = Approximation(
    "physical.eq.metal_spacing_k1_from_gate_baseline",
    metal_spacing_resolution_k1.symbol,
    gate_resolution_k1.symbol,
    gt(gate_resolution_k1.symbol, 0),
    "Minimum-metal-spacing k1 approximated from the shared Rayleigh/process-family gate k1 baseline.",
    references=[LITHOGRAPHY_K1_REF],
    check_units=True,
)


LITHOGRAPHY_K1_VARIABLES = [
    gate_resolution_k1,
    contact_resolution_k1,
    metal_width_resolution_k1,
    metal_spacing_resolution_k1,
    lithography_gate_k1_aerial_image_contrast_factor,
    lithography_gate_k1_resist_process_factor,
    lithography_gate_k1_mask_error_factor,
    lithography_gate_k1_resolution_enhancement_factor,
]

LITHOGRAPHY_K1_EQUATIONS = [
    eq_lithography_gate_k1_from_process_factors,
    eq_contact_resolution_k1_from_gate_baseline,
    eq_metal_width_resolution_k1_from_gate_baseline,
    eq_metal_spacing_resolution_k1_from_gate_baseline,
]

LITHOGRAPHY_K1_EXPORTS = [
    "LITHOGRAPHY_K1_REF",
    "gate_resolution_k1",
    "contact_resolution_k1",
    "metal_width_resolution_k1",
    "metal_spacing_resolution_k1",
    "lithography_gate_k1_aerial_image_contrast_factor",
    "lithography_gate_k1_resist_process_factor",
    "lithography_gate_k1_mask_error_factor",
    "lithography_gate_k1_resolution_enhancement_factor",
    "eq_lithography_gate_k1_from_process_factors",
    "eq_contact_resolution_k1_from_gate_baseline",
    "eq_metal_width_resolution_k1_from_gate_baseline",
    "eq_metal_spacing_resolution_k1_from_gate_baseline",
    "LITHOGRAPHY_K1_VARIABLES",
    "LITHOGRAPHY_K1_EQUATIONS",
    "LITHOGRAPHY_K1_EXPORTS",
]

__all__ = LITHOGRAPHY_K1_EXPORTS
