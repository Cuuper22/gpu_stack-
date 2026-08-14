"""Regression test for the precision low-bit module split.

The low-bit precision declarations were split into three submodules —
formats, training, and transforms — while the umbrella module
``precision_lowbit`` re-exports them as single tuples. Registration order
matters: variables and equations enter the registry in declaration order,
so a reshuffle would silently change the public ordering downstream code
sees.

This test pins both facts: the umbrella tuples are exactly the three
submodule tuples concatenated in formats-training-transforms order, and the
resulting name sequences match the published order element by element.
"""


def test_precision_lowbit_layers_preserve_public_order():
    from gpu_stack.scopes import precision_lowbit as lowbit
    from gpu_stack.scopes import precision_lowbit_formats as formats
    from gpu_stack.scopes import precision_lowbit_training as training
    from gpu_stack.scopes import precision_lowbit_transforms as transforms

    assert lowbit.PRECISION_LOWBIT_VARIABLES == (
        formats.PRECISION_LOWBIT_FORMAT_VARIABLES
        + training.PRECISION_LOWBIT_TRAINING_VARIABLES
        + transforms.PRECISION_LOWBIT_TRANSFORM_VARIABLES
    )
    assert lowbit.PRECISION_LOWBIT_EQUATIONS == (
        formats.PRECISION_LOWBIT_FORMAT_EQUATIONS
        + training.PRECISION_LOWBIT_TRAINING_EQUATIONS
        + transforms.PRECISION_LOWBIT_TRANSFORM_EQUATIONS
    )

    assert [v.name for v in lowbit.PRECISION_LOWBIT_VARIABLES] == [
        "precision.fp32.bytes",
        "precision.bf16.bytes",
        "precision.fp16.bytes",
        "precision.tf32.bytes",
        "precision.fp8.bytes",
        "precision.fp6.bytes",
        "precision.fp4.bytes",
        "precision.int8.bytes",
        "precision.int4.bytes",
        "precision.tf32.man_bits",
        "precision.posit.es",
        "precision.posit.useed",
        "precision.lns.log_step",
        "precision.lns.relative_error",
        "precision.throughput_ratio_vs_bf16",
        "precision.loss_scaling.grad_min_magnitude",
        "precision.loss_scaling.scale",
        "precision.loss_scaling.scaled_grad_min",
        "precision.loss_scaling.min_safe_scale",
        "precision.loss_scaling.grad_scaled",
        "precision.loss_scaling.grad_unscaled",
        "precision.rht.dim",
        "precision.rht.hadamard_matrix",
        "precision.rht.sign_diag",
        "precision.rht.input",
        "precision.rht.output",
        "precision.rht.scale",
        "precision.rht.input_norm",
        "precision.rht.output_norm",
        "precision.rht.outlier_in",
        "precision.rht.outlier_out",
    ]
    assert [e.name for e in lowbit.PRECISION_LOWBIT_EQUATIONS] == [
        "precision.eq.bytes_fp32",
        "precision.eq.bytes_bf16",
        "precision.eq.bytes_fp16",
        "precision.eq.bytes_tf32",
        "precision.eq.bytes_fp8",
        "precision.eq.bytes_fp6",
        "precision.eq.bytes_fp4",
        "precision.eq.bytes_int8",
        "precision.eq.bytes_int4",
        "precision.eq.tf32_man_bits",
        "precision.eq.posit_useed",
        "precision.eq.lns_relative_error",
        "precision.eq.scaled_grad_min",
        "precision.eq.min_loss_scale_safe",
        "precision.eq.grad_unscaled",
        "precision.eq.rht_scale",
        "precision.eq.rht_output",
        "precision.eq.rht_norm_preservation",
        "precision.eq.rht_outlier_spread",
    ]
