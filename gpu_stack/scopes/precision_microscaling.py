"""
scopes/precision_microscaling.py
================================

Microscaling and its relatives: sharing scale factors across small blocks
of values. In MX-style formats a block of (say) 32 low-bit elements shares
one scale factor, and NVFP4-style adds a second-level scale shared across
many blocks; the effective bits per value is the element width plus the
scale bits amortized over the block. Block floating point does the same
with a shared exponent, and dynamic fixed point reduces the scale to a
software-chosen fraction width. The effective-bits accounting is what lets
the training memory model price these formats honestly.
"""

import sympy as sp

from ..core import Reference, eq, var
from ..core.units import bit
from .precision_ieee import n_bits


DIMENSIONLESS = sp.Integer(1)

MICROSCALING_REF = Reference(
    "Open Compute Project, Microscaling Formats (MX) Specification, 2023.",
    kind="standard",
    year=2023,
)

BFP_REF = Reference(
    "Block floating point stores shared exponent metadata amortized across a block.",
    kind="model",
)

DYNAMIC_FIXED_POINT_REF = Reference(
    "Dynamic fixed-point quantization models use a local scale and fractional-bit step.",
    kind="model",
)


def _annotate_variables(variables, sp_units, references):
    for variable in variables:
        variable.sp_units = sp_units
        variable.references.extend(references)


# ---------------------------------------------------------------------------
# One scale per block: element bits plus amortized scale metadata give the real cost per value
# ---------------------------------------------------------------------------

block_size = var(
    "precision.microscale.block_size", "B_blk_ms", "elements",
    "Number of values sharing one microscale factor.",
    scope="precision",
)
scale_bits = var(
    "precision.microscale.scale_bits", "b_scale_ms", "bit",
    "Bits used for the first-level per-block scale.",
    scope="precision",
)
second_scale_bits = var(
    "precision.microscale.second_scale_bits", "b_scale2_ms", "bit",
    "Bits used for the optional second-level tensor scale.",
    scope="precision",
)
second_scale_fanout = var(
    "precision.microscale.second_scale_fanout", "N_scale2_ms", "elements",
    "Number of values amortizing one second-level scale.",
    scope="precision",
)
eff_bits_per_val = var(
    "precision.microscale.effective_bits", "b_eff_ms", "bit",
    "Effective bits per value after amortizing scale metadata.",
    scope="precision",
)
bfp_block_size = var(
    "precision.bfp.block_size", "B_blk_bfp", "elements",
    "Block size for block-floating-point.",
    scope="precision",
)
bfp_shared_exp_bits = var(
    "precision.bfp.shared_exp_bits", "b_exp_bfp", "bit",
    "Shared exponent bits per BFP block.",
    scope="precision",
)
bfp_eff_bits = var(
    "precision.bfp.effective_bits", "b_eff_bfp", "bit",
    "Effective bits per BFP value including amortized shared exponent overhead.",
    scope="precision",
)
fixed_frac_bits = var(
    "precision.fixed.frac_bits", "b_frac_fix", "bit",
    "Fractional bits in a dynamic fixed-point format.",
    scope="precision",
)
fixed_scale = var(
    "precision.fixed.scale", "s_fix", "value",
    "Dynamic fixed-point scale factor for one least-significant step.",
    scope="precision",
)

_annotate_variables(
    (
        block_size,
        second_scale_fanout,
    ),
    DIMENSIONLESS,
    [MICROSCALING_REF],
)
_annotate_variables(
    (
        scale_bits,
        second_scale_bits,
        eff_bits_per_val,
    ),
    bit,
    [MICROSCALING_REF],
)
_annotate_variables((bfp_block_size,), DIMENSIONLESS, [BFP_REF])
_annotate_variables((bfp_shared_exp_bits, bfp_eff_bits), bit, [BFP_REF])
_annotate_variables((fixed_frac_bits,), bit, [DYNAMIC_FIXED_POINT_REF])
_annotate_variables((fixed_scale,), DIMENSIONLESS, [DYNAMIC_FIXED_POINT_REF])


eq_effective_bits = eq(
    "precision.eq.effective_bits",
    eff_bits_per_val.symbol,
    (
        n_bits.symbol
        + scale_bits.symbol / block_size.symbol
        + second_scale_bits.symbol / second_scale_fanout.symbol
    ),
    "Effective bits per value equal payload bits plus amortized first-level and second-level scale overheads.",
    references=[MICROSCALING_REF],
    check_units=True,
)

eq_bfp_eff_bits = eq(
    "precision.eq.bfp_effective_bits",
    bfp_eff_bits.symbol,
    n_bits.symbol + bfp_shared_exp_bits.symbol / bfp_block_size.symbol,
    "BFP effective bits equal payload bits plus amortized shared exponent metadata.",
    references=[BFP_REF],
    check_units=True,
)

eq_fixed_scale = eq(
    "precision.eq.fixed_scale",
    fixed_scale.symbol,
    2 ** (-fixed_frac_bits.symbol),
    "A dynamic fixed-point step is 2^(-fractional_bits) in the chosen local scale frame.",
    references=[DYNAMIC_FIXED_POINT_REF],
)


PRECISION_MICROSCALING_VARIABLES = (
    block_size,
    scale_bits,
    second_scale_bits,
    second_scale_fanout,
    eff_bits_per_val,
    bfp_block_size,
    bfp_shared_exp_bits,
    bfp_eff_bits,
    fixed_frac_bits,
    fixed_scale,
)

PRECISION_MICROSCALING_EQUATIONS = (
    eq_effective_bits,
    eq_bfp_eff_bits,
    eq_fixed_scale,
)


__all__ = [
    "block_size",
    "scale_bits",
    "second_scale_bits",
    "second_scale_fanout",
    "eff_bits_per_val",
    "bfp_block_size",
    "bfp_shared_exp_bits",
    "bfp_eff_bits",
    "fixed_frac_bits",
    "fixed_scale",
    "eq_effective_bits",
    "eq_bfp_eff_bits",
    "eq_fixed_scale",
    "PRECISION_MICROSCALING_VARIABLES",
    "PRECISION_MICROSCALING_EQUATIONS",
]
