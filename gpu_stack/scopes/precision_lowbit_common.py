"""
scopes/precision_lowbit_common.py
=================================

Shared Reference objects and metadata helpers for the low-bit precision
modules, declared once so the formats, training, and transforms modules
cite the same provenance without importing each other.
"""

import sympy as sp

from ..core import Reference


DIMENSIONLESS = sp.Integer(1)

LOWBIT_STORAGE_REF = Reference(
    "Low-bit precision storage widths for FP32, BF16, FP16, TF32, FP8, "
    "FP6, FP4, INT8, and INT4.",
    kind="model",
)

TF32_REF = Reference(
    "NVIDIA TensorFloat-32 uses an FP32-range format with a 10-bit "
    "explicit mantissa in Tensor Core arithmetic.",
    kind="datasheet",
)

POSIT_LNS_REF = Reference(
    "Gustafson and Yonemoto, Beating Floating Point at its Own Game: "
    "Posit Arithmetic, 2017, and logarithmic number-system quantization models.",
    kind="paper",
    year=2017,
)

LOSS_SCALING_REF = Reference(
    "Micikevicius et al., Mixed Precision Training, 2017.",
    kind="paper",
    year=2017,
)

RHT_REF = Reference(
    "Randomized Hadamard transforms spread coordinate outliers while preserving "
    "vector norm.",
    kind="model",
)


def _annotate_variables(variables, sp_units, references):
    for variable in variables:
        variable.sp_units = sp_units
        variable.references.extend(references)
