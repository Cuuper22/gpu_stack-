"""
scopes/precision_lowbit_transforms.py
=====================================

Random Hadamard Transform declarations for microscaled low-bit formats.
"""

import sympy as sp

from ..core import Approximation, eq, var
from .precision_lowbit_common import (
    DIMENSIONLESS,
    RHT_REF,
    _annotate_variables,
)


rht_dim = var(
    "precision.rht.dim", "m_rht", "dimensionless",
    "Dimension of the Hadamard block.",
    scope="precision",
)
rht_hadamard = var(
    "precision.rht.hadamard_matrix", "H_rht", "matrix",
    "Hadamard matrix block used in the random rotation.",
    scope="precision",
)
rht_sign_diag = var(
    "precision.rht.sign_diag", "D_rht", "matrix",
    "Diagonal matrix of random plus-or-minus one signs.",
    scope="precision",
)
rht_input = var(
    "precision.rht.input", "x_rht_in", "vector",
    "Input vector before the random Hadamard rotation.",
    scope="precision",
)
rht_output = var(
    "precision.rht.output", "x_rht_out", "vector",
    "Output vector after the random Hadamard rotation.",
    scope="precision",
)
rht_scale = var(
    "precision.rht.scale", "s_rht", "dimensionless",
    "Normalization factor applied to the Hadamard transform.",
    scope="precision",
)
rht_input_norm = var(
    "precision.rht.input_norm", "n_rht_in", "value",
    "Input norm before rotation.",
    scope="precision",
)
rht_output_norm = var(
    "precision.rht.output_norm", "n_rht_out", "value",
    "Output norm after rotation.",
    scope="precision",
)
rht_outlier_in = var(
    "precision.rht.outlier_in", "o_rht_in", "value",
    "Representative coordinate outlier magnitude before rotation.",
    scope="precision",
)
rht_outlier_out = var(
    "precision.rht.outlier_out", "o_rht_out", "value",
    "Representative coordinate outlier magnitude after rotation.",
    scope="precision",
)

_annotate_variables(
    (
        rht_dim,
        rht_hadamard,
        rht_sign_diag,
        rht_input,
        rht_output,
        rht_scale,
        rht_input_norm,
        rht_output_norm,
        rht_outlier_in,
        rht_outlier_out,
    ),
    DIMENSIONLESS,
    [RHT_REF],
)


eq_rht_scale = eq(
    "precision.eq.rht_scale",
    rht_scale.symbol,
    1 / sp.sqrt(rht_dim.symbol),
    "The normalized Hadamard transform uses 1/sqrt(m).",
    references=[RHT_REF],
    check_units=True,
)

eq_rht_output = eq(
    "precision.eq.rht_output",
    rht_output.symbol,
    rht_hadamard.symbol * rht_sign_diag.symbol * rht_input.symbol * rht_scale.symbol,
    "The random Hadamard transform is H_m D x / sqrt(m), represented here with abstract matrix-valued factors.",
    references=[RHT_REF],
    check_units=True,
)

eq_rht_norm = eq(
    "precision.eq.rht_norm_preservation",
    rht_output_norm.symbol,
    rht_input_norm.symbol,
    "The normalized Hadamard transform preserves vector norm.",
    references=[RHT_REF],
    check_units=True,
)

eq_rht_outlier = Approximation(
    "precision.eq.rht_outlier_spread",
    rht_outlier_out.symbol,
    rht_outlier_in.symbol / sp.sqrt(rht_dim.symbol),
    sp.Abs(rht_outlier_in.symbol) > 0,
    "When an outlier is concentrated in one coordinate, a random Hadamard rotation spreads it across the block by about sqrt(m).",
    references=[RHT_REF],
    check_units=True,
)


PRECISION_LOWBIT_TRANSFORM_VARIABLES = (
    rht_dim,
    rht_hadamard,
    rht_sign_diag,
    rht_input,
    rht_output,
    rht_scale,
    rht_input_norm,
    rht_output_norm,
    rht_outlier_in,
    rht_outlier_out,
)

PRECISION_LOWBIT_TRANSFORM_EQUATIONS = (
    eq_rht_scale,
    eq_rht_output,
    eq_rht_norm,
    eq_rht_outlier,
)


__all__ = [
    "rht_dim",
    "rht_hadamard",
    "rht_sign_diag",
    "rht_input",
    "rht_output",
    "rht_scale",
    "rht_input_norm",
    "rht_output_norm",
    "rht_outlier_in",
    "rht_outlier_out",
    "eq_rht_scale",
    "eq_rht_output",
    "eq_rht_norm",
    "eq_rht_outlier",
]
