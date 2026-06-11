"""
scopes/physical_process.py
==========================

Process geometry anchors for the physical scope.

This module consumes lithographic critical dimensions and turns them into
front-end/back-end pitch abstractions used by local thermal and semiconductor
transport models.
"""

import sympy as sp

from ..core import Approximation, Inequality, Reference, var
from ..core.units import METER
from .physical_lithography import (
    LITHOGRAPHY_REF,
    contact_lithography_resolution,
    gate_lithography_resolution,
    metal_spacing_lithography_resolution,
    metal_width_lithography_resolution,
)


_PROCESS_GEOMETRY_REF = Reference(
    citation="Process-geometry abstraction: nominal node length from contacted gate pitch, minimum metal pitch, and a dimensionless naming/geometry factor",
    kind="memo",
)


L_channel = var(
    "physical.channel_length", "L_g", "m",
    "Physical channel or conduction-path length.",
    scope="physical",
    sp_units=METER,
    references=[_PROCESS_GEOMETRY_REF],
)
gate_length_lithography_bias = var(
    "physical.process.gate_length_lithography_bias", "Delta_L_gate_litho", "m",
    "Signed lithography, OPC, and etch bias applied to the gate critical dimension.",
    scope="physical",
    positive=False,
    sp_units=METER,
    references=[LITHOGRAPHY_REF],
)
drawn_gate_length = var(
    "physical.process.drawn_gate_length", "L_gate_drawn_proc", "m",
    "Drawn gate length component of the contacted gate pitch abstraction.",
    scope="physical",
    sp_units=METER,
    references=[_PROCESS_GEOMETRY_REF],
)
source_drain_contact_bias = var(
    "physical.process.source_drain_contact_bias", "Delta_W_sd_contact_proc", "m",
    "Signed lithography and etch bias applied to the source/drain contact critical dimension.",
    scope="physical",
    positive=False,
    sp_units=METER,
    references=[LITHOGRAPHY_REF],
)
source_drain_contact_width = var(
    "physical.process.source_drain_contact_width", "W_sd_contact_proc", "m",
    "Source/drain contact width component of the contacted gate pitch abstraction.",
    scope="physical",
    sp_units=METER,
    references=[_PROCESS_GEOMETRY_REF],
)
gate_contact_overlay_budget = var(
    "physical.process.gate_contact_overlay_budget", "O_gate_contact_proc", "m",
    "Single-sided overlay and registration allowance between the gate and source/drain contact.",
    scope="physical",
    sp_units=METER,
    references=[_PROCESS_GEOMETRY_REF],
)
gate_contact_enclosure_margin = var(
    "physical.process.gate_contact_enclosure_margin", "M_gate_contact_proc", "m",
    "Single-sided design-rule enclosure or process margin between gate edge and contact.",
    scope="physical",
    sp_units=METER,
    references=[_PROCESS_GEOMETRY_REF],
)
gate_contact_spacing = var(
    "physical.process.gate_contact_spacing", "S_gate_contact_proc", "m",
    "Single-sided spacing or enclosure between gate edge and source/drain contact.",
    scope="physical",
    sp_units=METER,
    references=[_PROCESS_GEOMETRY_REF],
)
contacted_gate_pitch = var(
    "physical.process.contacted_gate_pitch", "CPP_proc", "m",
    "Contacted gate pitch or comparable front-end pitch for the process abstraction.",
    scope="physical",
    sp_units=METER,
    references=[_PROCESS_GEOMETRY_REF],
)
metal_width_lithography_bias = var(
    "physical.process.minimum_metal_width_bias", "Delta_W_metal_min_proc", "m",
    "Signed lithography and etch bias applied to the minimum metal width.",
    scope="physical",
    positive=False,
    sp_units=METER,
    references=[LITHOGRAPHY_REF],
)
minimum_metal_width = var(
    "physical.process.minimum_metal_width", "W_metal_min_proc", "m",
    "Minimum routed metal width used by the process abstraction.",
    scope="physical",
    sp_units=METER,
    references=[_PROCESS_GEOMETRY_REF],
)
metal_spacing_lithography_bias = var(
    "physical.process.minimum_metal_spacing_bias", "Delta_S_metal_min_proc", "m",
    "Signed lithography and etch bias applied to the minimum metal spacing.",
    scope="physical",
    positive=False,
    sp_units=METER,
    references=[LITHOGRAPHY_REF],
)
minimum_metal_spacing = var(
    "physical.process.minimum_metal_spacing", "S_metal_min_proc", "m",
    "Minimum routed metal spacing used by the process abstraction.",
    scope="physical",
    sp_units=METER,
    references=[_PROCESS_GEOMETRY_REF],
)
minimum_metal_pitch = var(
    "physical.process.minimum_metal_pitch", "MMP_proc", "m",
    "Minimum routed metal pitch used as the back-end process geometry anchor.",
    scope="physical",
    sp_units=METER,
    references=[_PROCESS_GEOMETRY_REF],
)
node_geometry_factor = var(
    "physical.process.node_geometry_factor", "k_node_geom_proc", "dimensionless",
    "Dimensionless mapping from front-end/back-end pitch geometry to nominal node length.",
    scope="physical",
    positive=True,
    sp_units=sp.Integer(1),
    references=[_PROCESS_GEOMETRY_REF],
)
process_node_length = var(
    "physical.process.node_length", "L_node_proc", "m",
    "Nominal process-node length scale used as a symbolic geometry anchor.",
    scope="physical",
    sp_units=METER,
    references=[_PROCESS_GEOMETRY_REF],
)
gate_length_scale = var(
    "physical.process.gate_length_scale", "k_gate_len_proc", "dimensionless",
    "Scale factor from nominal process-node length to drawn or effective gate length.",
    scope="physical",
    sp_units=sp.Integer(1),
    references=[_PROCESS_GEOMETRY_REF],
)
gate_length_bias = var(
    "physical.process.gate_length_bias", "Delta_L_gate_proc", "m",
    "Signed process and layout bias added to the scaled nominal gate length.",
    scope="physical",
    positive=False,
    sp_units=METER,
    references=[_PROCESS_GEOMETRY_REF],
)


eq_drawn_gate_length = Approximation(
    "physical.eq.drawn_gate_length",
    drawn_gate_length.symbol,
    gate_lithography_resolution.symbol + gate_length_lithography_bias.symbol,
    gate_lithography_resolution.symbol > 0,
    "Drawn gate length from lithographic gate resolution plus signed process bias.",
    references=[LITHOGRAPHY_REF],
    check_units=True,
)

eq_source_drain_contact_width = Approximation(
    "physical.eq.source_drain_contact_width",
    source_drain_contact_width.symbol,
    contact_lithography_resolution.symbol + source_drain_contact_bias.symbol,
    contact_lithography_resolution.symbol > 0,
    "Source/drain contact width from lithographic contact resolution plus signed process bias.",
    references=[LITHOGRAPHY_REF],
    check_units=True,
)

eq_gate_contact_spacing = Approximation(
    "physical.eq.gate_contact_spacing",
    gate_contact_spacing.symbol,
    gate_contact_overlay_budget.symbol + gate_contact_enclosure_margin.symbol,
    (gate_contact_overlay_budget.symbol >= 0)
    & (gate_contact_enclosure_margin.symbol >= 0),
    "Gate-contact spacing from overlay budget plus single-sided enclosure margin.",
    references=[_PROCESS_GEOMETRY_REF],
    check_units=True,
)

eq_minimum_metal_width = Approximation(
    "physical.eq.minimum_metal_width",
    minimum_metal_width.symbol,
    metal_width_lithography_resolution.symbol
    + metal_width_lithography_bias.symbol,
    metal_width_lithography_resolution.symbol > 0,
    "Minimum metal width from lithographic metal-width resolution plus signed process bias.",
    references=[LITHOGRAPHY_REF],
    check_units=True,
)

eq_minimum_metal_spacing = Approximation(
    "physical.eq.minimum_metal_spacing",
    minimum_metal_spacing.symbol,
    metal_spacing_lithography_resolution.symbol
    + metal_spacing_lithography_bias.symbol,
    metal_spacing_lithography_resolution.symbol > 0,
    "Minimum metal spacing from lithographic spacing resolution plus signed process bias.",
    references=[LITHOGRAPHY_REF],
    check_units=True,
)

eq_contacted_gate_pitch = Approximation(
    "physical.eq.contacted_gate_pitch",
    contacted_gate_pitch.symbol,
    drawn_gate_length.symbol
    + source_drain_contact_width.symbol
    + 2 * gate_contact_spacing.symbol,
    (
        (drawn_gate_length.symbol > 0)
        & (source_drain_contact_width.symbol > 0)
        & (gate_contact_spacing.symbol >= 0)
    ),
    "Contacted gate pitch from drawn gate length, source/drain contact width, and two single-sided gate-contact spacings.",
    references=[_PROCESS_GEOMETRY_REF],
    check_units=True,
)

eq_minimum_metal_pitch = Approximation(
    "physical.eq.minimum_metal_pitch",
    minimum_metal_pitch.symbol,
    minimum_metal_width.symbol + minimum_metal_spacing.symbol,
    (minimum_metal_width.symbol > 0) & (minimum_metal_spacing.symbol > 0),
    "Minimum metal pitch from minimum routed metal width and minimum spacing.",
    references=[_PROCESS_GEOMETRY_REF],
    check_units=True,
)

eq_process_node_from_pitches = Approximation(
    "physical.eq.process_node_from_pitches",
    process_node_length.symbol,
    node_geometry_factor.symbol
    * sp.sqrt(contacted_gate_pitch.symbol * minimum_metal_pitch.symbol),
    (contacted_gate_pitch.symbol > 0) & (minimum_metal_pitch.symbol > 0),
    "Nominal process-node length approximated from the geometric mean of contacted gate pitch and minimum metal pitch, scaled by a dimensionless process naming factor.",
    references=[_PROCESS_GEOMETRY_REF],
    check_units=True,
)

eq_channel_length_process = Approximation(
    "physical.eq.channel_length_process",
    L_channel.symbol,
    process_node_length.symbol * gate_length_scale.symbol + gate_length_bias.symbol,
    process_node_length.symbol > 0,
    "Effective channel length approximated from nominal process geometry, gate-length scaling, and signed process/layout bias.",
    references=[_PROCESS_GEOMETRY_REF],
    check_units=True,
)

ineq_drawn_gate_length_positive = Inequality(
    "physical.ineq.drawn_gate_length_positive",
    drawn_gate_length.symbol,
    sp.Integer(0),
    ">",
    "Drawn gate length must remain positive after signed lithography and etch bias.",
    references=[_PROCESS_GEOMETRY_REF],
)
ineq_source_drain_contact_width_positive = Inequality(
    "physical.ineq.source_drain_contact_width_positive",
    source_drain_contact_width.symbol,
    sp.Integer(0),
    ">",
    "Source/drain contact width must remain positive after signed process bias.",
    references=[_PROCESS_GEOMETRY_REF],
)
ineq_gate_contact_spacing_nonnegative = Inequality(
    "physical.ineq.gate_contact_spacing_nonnegative",
    gate_contact_spacing.symbol,
    sp.Integer(0),
    ">=",
    "Gate-contact spacing should not become negative after overlay and enclosure allowances.",
    references=[_PROCESS_GEOMETRY_REF],
)
ineq_contacted_gate_pitch_positive = Inequality(
    "physical.ineq.contacted_gate_pitch_positive",
    contacted_gate_pitch.symbol,
    sp.Integer(0),
    ">",
    "Contacted gate pitch must remain positive after combining gate, contact, and spacing components.",
    references=[_PROCESS_GEOMETRY_REF],
)
ineq_minimum_metal_width_positive = Inequality(
    "physical.ineq.minimum_metal_width_positive",
    minimum_metal_width.symbol,
    sp.Integer(0),
    ">",
    "Minimum metal width must remain positive after signed lithography and etch bias.",
    references=[_PROCESS_GEOMETRY_REF],
)
ineq_minimum_metal_spacing_positive = Inequality(
    "physical.ineq.minimum_metal_spacing_positive",
    minimum_metal_spacing.symbol,
    sp.Integer(0),
    ">",
    "Minimum metal spacing must remain positive after signed lithography and etch bias.",
    references=[_PROCESS_GEOMETRY_REF],
)
ineq_minimum_metal_pitch_positive = Inequality(
    "physical.ineq.minimum_metal_pitch_positive",
    minimum_metal_pitch.symbol,
    sp.Integer(0),
    ">",
    "Minimum metal pitch must remain positive after width and spacing closure.",
    references=[_PROCESS_GEOMETRY_REF],
)
ineq_process_node_length_positive = Inequality(
    "physical.ineq.process_node_length_positive",
    process_node_length.symbol,
    sp.Integer(0),
    ">",
    "Nominal process-node length must remain positive after pitch geometry scaling.",
    references=[_PROCESS_GEOMETRY_REF],
)
ineq_channel_length_positive = Inequality(
    "physical.ineq.channel_length_positive",
    L_channel.symbol,
    sp.Integer(0),
    ">",
    "Effective channel length must remain positive after signed process/layout bias.",
    references=[_PROCESS_GEOMETRY_REF],
)


PROCESS_VARIABLES = [
    L_channel,
    gate_length_lithography_bias,
    drawn_gate_length,
    source_drain_contact_bias,
    source_drain_contact_width,
    gate_contact_overlay_budget,
    gate_contact_enclosure_margin,
    gate_contact_spacing,
    contacted_gate_pitch,
    metal_width_lithography_bias,
    minimum_metal_width,
    metal_spacing_lithography_bias,
    minimum_metal_spacing,
    minimum_metal_pitch,
    node_geometry_factor,
    process_node_length,
    gate_length_scale,
    gate_length_bias,
]

PROCESS_EQUATIONS = [
    eq_drawn_gate_length,
    eq_source_drain_contact_width,
    eq_gate_contact_spacing,
    eq_minimum_metal_width,
    eq_minimum_metal_spacing,
    eq_contacted_gate_pitch,
    eq_minimum_metal_pitch,
    eq_process_node_from_pitches,
    eq_channel_length_process,
    ineq_drawn_gate_length_positive,
    ineq_source_drain_contact_width_positive,
    ineq_gate_contact_spacing_nonnegative,
    ineq_contacted_gate_pitch_positive,
    ineq_minimum_metal_width_positive,
    ineq_minimum_metal_spacing_positive,
    ineq_minimum_metal_pitch_positive,
    ineq_process_node_length_positive,
    ineq_channel_length_positive,
]


__all__ = [
    "L_channel",
    "gate_length_lithography_bias",
    "drawn_gate_length",
    "source_drain_contact_bias",
    "source_drain_contact_width",
    "gate_contact_overlay_budget",
    "gate_contact_enclosure_margin",
    "gate_contact_spacing",
    "contacted_gate_pitch",
    "metal_width_lithography_bias",
    "minimum_metal_width",
    "metal_spacing_lithography_bias",
    "minimum_metal_spacing",
    "minimum_metal_pitch",
    "node_geometry_factor",
    "process_node_length",
    "gate_length_scale",
    "gate_length_bias",
    "eq_drawn_gate_length",
    "eq_source_drain_contact_width",
    "eq_gate_contact_spacing",
    "eq_minimum_metal_width",
    "eq_minimum_metal_spacing",
    "eq_contacted_gate_pitch",
    "eq_minimum_metal_pitch",
    "eq_process_node_from_pitches",
    "eq_channel_length_process",
    "ineq_drawn_gate_length_positive",
    "ineq_source_drain_contact_width_positive",
    "ineq_gate_contact_spacing_nonnegative",
    "ineq_contacted_gate_pitch_positive",
    "ineq_minimum_metal_width_positive",
    "ineq_minimum_metal_spacing_positive",
    "ineq_minimum_metal_pitch_positive",
    "ineq_process_node_length_positive",
    "ineq_channel_length_positive",
    "PROCESS_VARIABLES",
    "PROCESS_EQUATIONS",
]
