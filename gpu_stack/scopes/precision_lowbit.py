"""
scopes/precision_lowbit.py
==========================

Compatibility surface for low-bit formats and their supporting
transforms. Byte widths for FP32 down to INT4, TF32 mantissa structure,
posit and logarithmic number systems, FP16 loss scaling, and the Random
Hadamard Transform live in focused sibling modules (formats, training,
transforms, common); this module re-exports them so public imports stay
stable.
"""

import sympy as sp

from ..core import Approximation, Reference, eq, var
from ..core.units import bit, byte
from .precision_ieee import min_normal
from .precision_lowbit_common import (
    DIMENSIONLESS,
    LOWBIT_STORAGE_REF,
    LOSS_SCALING_REF,
    POSIT_LNS_REF,
    RHT_REF,
    TF32_REF,
    _annotate_variables,
)
from .precision_lowbit_formats import *
from .precision_lowbit_formats import (
    PRECISION_LOWBIT_FORMAT_EQUATIONS as _PRECISION_LOWBIT_FORMAT_EQUATIONS,
    PRECISION_LOWBIT_FORMAT_VARIABLES as _PRECISION_LOWBIT_FORMAT_VARIABLES,
)
from .precision_lowbit_training import *
from .precision_lowbit_training import (
    PRECISION_LOWBIT_TRAINING_EQUATIONS as _PRECISION_LOWBIT_TRAINING_EQUATIONS,
    PRECISION_LOWBIT_TRAINING_VARIABLES as _PRECISION_LOWBIT_TRAINING_VARIABLES,
)
from .precision_lowbit_transforms import *
from .precision_lowbit_transforms import (
    PRECISION_LOWBIT_TRANSFORM_EQUATIONS as _PRECISION_LOWBIT_TRANSFORM_EQUATIONS,
    PRECISION_LOWBIT_TRANSFORM_VARIABLES as _PRECISION_LOWBIT_TRANSFORM_VARIABLES,
)


PRECISION_LOWBIT_VARIABLES = (
    _PRECISION_LOWBIT_FORMAT_VARIABLES
    + _PRECISION_LOWBIT_TRAINING_VARIABLES
    + _PRECISION_LOWBIT_TRANSFORM_VARIABLES
)

PRECISION_LOWBIT_EQUATIONS = (
    _PRECISION_LOWBIT_FORMAT_EQUATIONS
    + _PRECISION_LOWBIT_TRAINING_EQUATIONS
    + _PRECISION_LOWBIT_TRANSFORM_EQUATIONS
)


__all__ = [
    "bytes_fp32",
    "bytes_bf16",
    "bytes_fp16",
    "bytes_tf32",
    "bytes_fp8",
    "bytes_fp6",
    "bytes_fp4",
    "bytes_int8",
    "bytes_int4",
    "tf32_man_bits",
    "posit_es",
    "posit_useed",
    "lns_step",
    "lns_rel_error",
    "ratio_vs_bf16",
    "grad_min_magnitude",
    "loss_scale",
    "scaled_grad_min",
    "min_loss_scale_safe",
    "grad_scaled",
    "grad_unscaled",
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
    "eq_bytes_fp32",
    "eq_bytes_bf16",
    "eq_bytes_fp16",
    "eq_bytes_tf32",
    "eq_bytes_fp8",
    "eq_bytes_fp6",
    "eq_bytes_fp4",
    "eq_bytes_int8",
    "eq_bytes_int4",
    "eq_tf32_man_bits",
    "eq_posit_useed",
    "eq_lns_rel_error",
    "eq_scaled_grad_min",
    "eq_min_loss_scale_safe",
    "eq_grad_unscaled",
    "eq_rht_scale",
    "eq_rht_output",
    "eq_rht_norm",
    "eq_rht_outlier",
    "PRECISION_LOWBIT_VARIABLES",
    "PRECISION_LOWBIT_EQUATIONS",
]
