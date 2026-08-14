"""
scopes/physical_lithography_plasma_overlap.py
=============================================

Overlap between the drive pulse and the emitting plasma, in space and in
time. Spatially, pointing error (centroid offset over column radius) and
transverse size mismatch each cost a factor; temporally, a timing offset
and a duration mismatch between the pulse and the plasma response cost two
more. The product of the spatial and temporal factors is the overall
overlap factor, a number between 0 and 1 that multiplies the absorption
efficiency: drive energy that misses the plasma in space or arrives at the
wrong time heats nothing.
"""

import sympy as sp

from ..core import Approximation, Inequality, var
from ..core.units import SECOND
from .physical_lithography_plasma_drive import (
    lithography_source_plasma_active_fill_factor,
    lithography_source_plasma_column_radius,
    lithography_source_plasma_drive_pulse_duration,
)
from .physical_lithography_plasma_focus import (
    lithography_source_plasma_drive_spot_area,
)
from .physical_lithography_plasma_species import LITHOGRAPHY_SOURCE_PLASMA_STATE_REF


lithography_source_plasma_drive_centroid_offset_to_column_radius_ratio = var(
    "physical.lithography.source_plasma_drive_centroid_offset_to_column_radius_ratio",
    "rho_offset_drive_col_litho_src",
    "dimensionless",
    "Drive-spot centroid offset normalized by source-plasma column radius.",
    scope="physical",
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
)
lithography_source_plasma_drive_pointing_overlap_factor = var(
    "physical.lithography.source_plasma_drive_pointing_overlap_factor",
    "eta_pointing_drive_litho_src",
    "dimensionless",
    "Drive-plasma pointing overlap factor from normalized spot-to-column centroid offset.",
    scope="physical",
    positive=True,
    value_range=(0.0, 1.0),
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
)
lithography_source_plasma_drive_transverse_overlap_factor = var(
    "physical.lithography.source_plasma_drive_transverse_overlap_factor",
    "eta_transverse_drive_litho_src",
    "dimensionless",
    "Transverse source-plasma drive overlap from illuminated spot area over column cross-section.",
    scope="physical",
    positive=True,
    value_range=(0.0, 1.0),
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
)
lithography_source_plasma_drive_spatial_overlap_factor = var(
    "physical.lithography.source_plasma_drive_spatial_overlap_factor",
    "eta_spatial_drive_litho_src",
    "dimensionless",
    "Spatial drive-plasma overlap from transverse coverage, pointing, and active column fill.",
    scope="physical",
    positive=True,
    value_range=(0.0, 1.0),
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
)
lithography_source_plasma_active_lifetime_to_drive_pulse_ratio = var(
    "physical.lithography.source_plasma_active_lifetime_to_drive_pulse_ratio",
    "rho_tau_active_drive_litho_src",
    "dimensionless",
    "Active plasma response lifetime normalized by drive pulse duration.",
    scope="physical",
    positive=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
)
lithography_source_plasma_active_response_duration = var(
    "physical.lithography.source_plasma_active_response_duration",
    "tau_active_plasma_litho_src",
    "s",
    "Effective active-plasma response duration for temporal overlap with the drive pulse.",
    scope="physical",
    positive=True,
    sp_units=SECOND,
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
)
lithography_source_plasma_drive_timing_offset_fraction = var(
    "physical.lithography.source_plasma_drive_timing_offset_fraction",
    "rho_timing_offset_drive_litho_src",
    "dimensionless",
    "Drive-to-active-plasma timing offset normalized by drive pulse duration.",
    scope="physical",
    nonnegative=True,
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
)
lithography_source_plasma_drive_timing_offset_duration = var(
    "physical.lithography.source_plasma_drive_timing_offset_duration",
    "dt_timing_offset_drive_litho_src",
    "s",
    "Absolute timing offset between the drive pulse and active plasma response.",
    scope="physical",
    nonnegative=True,
    sp_units=SECOND,
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
)
lithography_source_plasma_drive_temporal_duration_match_factor = var(
    "physical.lithography.source_plasma_drive_temporal_duration_match_factor",
    "eta_duration_match_drive_litho_src",
    "dimensionless",
    "Temporal overlap factor from duration matching between drive pulse and active plasma response.",
    scope="physical",
    positive=True,
    value_range=(0.0, 1.0),
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
)
lithography_source_plasma_drive_temporal_alignment_factor = var(
    "physical.lithography.source_plasma_drive_temporal_alignment_factor",
    "eta_temporal_alignment_drive_litho_src",
    "dimensionless",
    "Temporal alignment factor from timing offset between drive pulse and active plasma response.",
    scope="physical",
    positive=True,
    value_range=(0.0, 1.0),
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
)
lithography_source_plasma_drive_temporal_overlap_factor = var(
    "physical.lithography.source_plasma_drive_temporal_overlap_factor",
    "eta_temporal_drive_litho_src",
    "dimensionless",
    "Temporal drive-plasma overlap from response-duration match and timing alignment.",
    scope="physical",
    positive=True,
    value_range=(0.0, 1.0),
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
)
lithography_source_plasma_drive_overlap_factor = var(
    "physical.lithography.source_plasma_drive_overlap_factor",
    "eta_overlap_plasma_litho_src",
    "dimensionless",
    "Geometric and temporal overlap factor between the drive pulse and active plasma.",
    scope="physical",
    positive=True,
    value_range=(0.0, 1.0),
    sp_units=sp.Integer(1),
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
)

eq_lithography_source_plasma_drive_centroid_offset_to_column_radius_ratio_from_coaxial_convention = Approximation(
    "physical.eq.lithography_source_plasma_drive_centroid_offset_to_column_radius_ratio_from_coaxial_convention",
    lithography_source_plasma_drive_centroid_offset_to_column_radius_ratio.symbol,
    sp.Integer(0),
    sp.S.true,
    "Coaxial drive-column convention where the drive spot is centered on the source plasma column.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_drive_pointing_overlap_factor_from_offset = Approximation(
    "physical.eq.lithography_source_plasma_drive_pointing_overlap_factor_from_offset",
    lithography_source_plasma_drive_pointing_overlap_factor.symbol,
    sp.exp(
        -lithography_source_plasma_drive_centroid_offset_to_column_radius_ratio.symbol**2
    ),
    lithography_source_plasma_drive_centroid_offset_to_column_radius_ratio.symbol >= 0,
    "Drive-plasma pointing overlap from a Gaussian penalty on normalized centroid offset.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_drive_transverse_overlap_factor_from_area_ratio = Approximation(
    "physical.eq.lithography_source_plasma_drive_transverse_overlap_factor_from_area_ratio",
    lithography_source_plasma_drive_transverse_overlap_factor.symbol,
    (
        lithography_source_plasma_drive_spot_area.symbol
        / (sp.pi * lithography_source_plasma_column_radius.symbol**2)
    ),
    (
        (lithography_source_plasma_drive_spot_area.symbol > 0)
        & (lithography_source_plasma_column_radius.symbol > 0)
        & (
            lithography_source_plasma_drive_spot_area.symbol
            <= sp.pi * lithography_source_plasma_column_radius.symbol**2
        )
    ),
    "Transverse overlap from drive spot area divided by plasma column cross-section.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
ineq_lithography_source_plasma_drive_spot_area_within_column_cross_section = Inequality(
    "physical.ineq.lithography_source_plasma_drive_spot_area_within_column_cross_section",
    lithography_source_plasma_drive_spot_area.symbol,
    sp.pi * lithography_source_plasma_column_radius.symbol**2,
    "<=",
    "Drive spot area should fit within the source plasma column cross-section for the transverse-overlap approximation.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_drive_spatial_overlap_factor_from_geometry = Approximation(
    "physical.eq.lithography_source_plasma_drive_spatial_overlap_factor_from_geometry",
    lithography_source_plasma_drive_spatial_overlap_factor.symbol,
    (
        lithography_source_plasma_drive_transverse_overlap_factor.symbol
        * lithography_source_plasma_drive_pointing_overlap_factor.symbol
        * lithography_source_plasma_active_fill_factor.symbol
    ),
    (
        (lithography_source_plasma_drive_transverse_overlap_factor.symbol > 0)
        & (lithography_source_plasma_drive_transverse_overlap_factor.symbol <= 1)
        & (lithography_source_plasma_drive_pointing_overlap_factor.symbol > 0)
        & (lithography_source_plasma_drive_pointing_overlap_factor.symbol <= 1)
        & (lithography_source_plasma_active_fill_factor.symbol > 0)
        & (lithography_source_plasma_active_fill_factor.symbol <= 1)
    ),
    "Spatial drive-plasma overlap from transverse coverage, pointing, and active fill.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_active_response_duration_from_drive_ratio = Approximation(
    "physical.eq.lithography_source_plasma_active_response_duration_from_drive_ratio",
    lithography_source_plasma_active_response_duration.symbol,
    (
        lithography_source_plasma_active_lifetime_to_drive_pulse_ratio.symbol
        * lithography_source_plasma_drive_pulse_duration.symbol
    ),
    (
        (lithography_source_plasma_active_lifetime_to_drive_pulse_ratio.symbol > 0)
        & (lithography_source_plasma_drive_pulse_duration.symbol > 0)
    ),
    "Active plasma response duration from lifetime-to-drive-pulse ratio.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_drive_timing_offset_fraction_from_synchronized_convention = Approximation(
    "physical.eq.lithography_source_plasma_drive_timing_offset_fraction_from_synchronized_convention",
    lithography_source_plasma_drive_timing_offset_fraction.symbol,
    sp.Integer(0),
    sp.S.true,
    "Synchronized drive convention where the active plasma response is centered on the drive pulse.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_drive_timing_offset_duration_from_fraction = Approximation(
    "physical.eq.lithography_source_plasma_drive_timing_offset_duration_from_fraction",
    lithography_source_plasma_drive_timing_offset_duration.symbol,
    (
        lithography_source_plasma_drive_timing_offset_fraction.symbol
        * lithography_source_plasma_drive_pulse_duration.symbol
    ),
    (
        (lithography_source_plasma_drive_timing_offset_fraction.symbol >= 0)
        & (lithography_source_plasma_drive_pulse_duration.symbol > 0)
    ),
    "Drive-to-active-plasma timing offset duration from pulse-normalized offset.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_drive_temporal_duration_match_factor = Approximation(
    "physical.eq.lithography_source_plasma_drive_temporal_duration_match_factor",
    lithography_source_plasma_drive_temporal_duration_match_factor.symbol,
    (
        sp.Integer(4)
        * lithography_source_plasma_drive_pulse_duration.symbol
        * lithography_source_plasma_active_response_duration.symbol
        / (
            lithography_source_plasma_drive_pulse_duration.symbol
            + lithography_source_plasma_active_response_duration.symbol
        )**2
    ),
    (
        (lithography_source_plasma_drive_pulse_duration.symbol > 0)
        & (lithography_source_plasma_active_response_duration.symbol > 0)
    ),
    "Temporal duration-match factor between drive pulse and active plasma response.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_drive_temporal_alignment_factor_from_timing_offset = Approximation(
    "physical.eq.lithography_source_plasma_drive_temporal_alignment_factor_from_timing_offset",
    lithography_source_plasma_drive_temporal_alignment_factor.symbol,
    sp.exp(
        -(
            lithography_source_plasma_drive_timing_offset_duration.symbol
            / (
                lithography_source_plasma_drive_pulse_duration.symbol
                + lithography_source_plasma_active_response_duration.symbol
            )
        )**2
    ),
    (
        (lithography_source_plasma_drive_timing_offset_duration.symbol >= 0)
        & (lithography_source_plasma_drive_pulse_duration.symbol > 0)
        & (lithography_source_plasma_active_response_duration.symbol > 0)
    ),
    "Temporal alignment factor from timing offset relative to combined drive and response durations.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_drive_temporal_overlap_factor_from_duration_and_alignment = Approximation(
    "physical.eq.lithography_source_plasma_drive_temporal_overlap_factor_from_duration_and_alignment",
    lithography_source_plasma_drive_temporal_overlap_factor.symbol,
    (
        lithography_source_plasma_drive_temporal_duration_match_factor.symbol
        * lithography_source_plasma_drive_temporal_alignment_factor.symbol
    ),
    (
        (lithography_source_plasma_drive_temporal_duration_match_factor.symbol > 0)
        & (lithography_source_plasma_drive_temporal_duration_match_factor.symbol <= 1)
        & (lithography_source_plasma_drive_temporal_alignment_factor.symbol > 0)
        & (lithography_source_plasma_drive_temporal_alignment_factor.symbol <= 1)
    ),
    "Temporal drive-plasma overlap from duration match and timing alignment.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)
eq_lithography_source_plasma_drive_overlap_factor_from_spatial_temporal = Approximation(
    "physical.eq.lithography_source_plasma_drive_overlap_factor_from_spatial_temporal",
    lithography_source_plasma_drive_overlap_factor.symbol,
    (
        lithography_source_plasma_drive_spatial_overlap_factor.symbol
        * lithography_source_plasma_drive_temporal_overlap_factor.symbol
    ),
    (
        (lithography_source_plasma_drive_spatial_overlap_factor.symbol > 0)
        & (lithography_source_plasma_drive_spatial_overlap_factor.symbol <= 1)
        & (lithography_source_plasma_drive_temporal_overlap_factor.symbol > 0)
        & (lithography_source_plasma_drive_temporal_overlap_factor.symbol <= 1)
    ),
    "Total drive-plasma overlap from spatial and temporal overlap factors.",
    references=[LITHOGRAPHY_SOURCE_PLASMA_STATE_REF],
    check_units=True,
)


LITHOGRAPHY_SOURCE_PLASMA_OVERLAP_VARIABLES = [
    lithography_source_plasma_drive_centroid_offset_to_column_radius_ratio,
    lithography_source_plasma_drive_pointing_overlap_factor,
    lithography_source_plasma_drive_transverse_overlap_factor,
    lithography_source_plasma_drive_spatial_overlap_factor,
    lithography_source_plasma_active_lifetime_to_drive_pulse_ratio,
    lithography_source_plasma_active_response_duration,
    lithography_source_plasma_drive_timing_offset_fraction,
    lithography_source_plasma_drive_timing_offset_duration,
    lithography_source_plasma_drive_temporal_duration_match_factor,
    lithography_source_plasma_drive_temporal_alignment_factor,
    lithography_source_plasma_drive_temporal_overlap_factor,
    lithography_source_plasma_drive_overlap_factor,
]

LITHOGRAPHY_SOURCE_PLASMA_OVERLAP_EQUATIONS = [
    eq_lithography_source_plasma_drive_centroid_offset_to_column_radius_ratio_from_coaxial_convention,
    eq_lithography_source_plasma_drive_pointing_overlap_factor_from_offset,
    eq_lithography_source_plasma_drive_transverse_overlap_factor_from_area_ratio,
    ineq_lithography_source_plasma_drive_spot_area_within_column_cross_section,
    eq_lithography_source_plasma_drive_spatial_overlap_factor_from_geometry,
    eq_lithography_source_plasma_active_response_duration_from_drive_ratio,
    eq_lithography_source_plasma_drive_timing_offset_fraction_from_synchronized_convention,
    eq_lithography_source_plasma_drive_timing_offset_duration_from_fraction,
    eq_lithography_source_plasma_drive_temporal_duration_match_factor,
    eq_lithography_source_plasma_drive_temporal_alignment_factor_from_timing_offset,
    eq_lithography_source_plasma_drive_temporal_overlap_factor_from_duration_and_alignment,
    eq_lithography_source_plasma_drive_overlap_factor_from_spatial_temporal,
]

LITHOGRAPHY_SOURCE_PLASMA_OVERLAP_EXPORTS = [
    "lithography_source_plasma_drive_centroid_offset_to_column_radius_ratio",
    "lithography_source_plasma_drive_pointing_overlap_factor",
    "lithography_source_plasma_drive_transverse_overlap_factor",
    "lithography_source_plasma_drive_spatial_overlap_factor",
    "lithography_source_plasma_active_lifetime_to_drive_pulse_ratio",
    "lithography_source_plasma_active_response_duration",
    "lithography_source_plasma_drive_timing_offset_fraction",
    "lithography_source_plasma_drive_timing_offset_duration",
    "lithography_source_plasma_drive_temporal_duration_match_factor",
    "lithography_source_plasma_drive_temporal_alignment_factor",
    "lithography_source_plasma_drive_temporal_overlap_factor",
    "lithography_source_plasma_drive_overlap_factor",
    "eq_lithography_source_plasma_drive_centroid_offset_to_column_radius_ratio_from_coaxial_convention",
    "eq_lithography_source_plasma_drive_pointing_overlap_factor_from_offset",
    "eq_lithography_source_plasma_drive_transverse_overlap_factor_from_area_ratio",
    "ineq_lithography_source_plasma_drive_spot_area_within_column_cross_section",
    "eq_lithography_source_plasma_drive_spatial_overlap_factor_from_geometry",
    "eq_lithography_source_plasma_active_response_duration_from_drive_ratio",
    "eq_lithography_source_plasma_drive_timing_offset_fraction_from_synchronized_convention",
    "eq_lithography_source_plasma_drive_timing_offset_duration_from_fraction",
    "eq_lithography_source_plasma_drive_temporal_duration_match_factor",
    "eq_lithography_source_plasma_drive_temporal_alignment_factor_from_timing_offset",
    "eq_lithography_source_plasma_drive_temporal_overlap_factor_from_duration_and_alignment",
    "eq_lithography_source_plasma_drive_overlap_factor_from_spatial_temporal",
    "LITHOGRAPHY_SOURCE_PLASMA_OVERLAP_VARIABLES",
    "LITHOGRAPHY_SOURCE_PLASMA_OVERLAP_EQUATIONS",
]

__all__ = LITHOGRAPHY_SOURCE_PLASMA_OVERLAP_EXPORTS
