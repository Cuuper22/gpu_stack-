"""
tests/test_lithography_k1_strict.py
===================================

Gate k1 is computed from four process factors, and each factor has a physical
domain: contrast factors cannot exceed 1, and none can be zero or negative.
This module feeds deliberately impossible factor values through two paths and
checks that both refuse to pass them silently. The library path (resolve)
must mark the matching domain constraint as unsatisfied; the CLI path, run
with --fail-on-violated-constraints, must print the violated constraint and
exit with a nonzero return code so scripts and CI can catch the bad input.
"""

import contextlib
import io
import sys

import pytest

from gpu_stack import resolve
from gpu_stack.cli import main


VALID_GATE_K1_PROCESS_FACTOR_ASSIGNMENTS = {
    "physical.lithography.gate_k1_aerial_image_contrast_factor": 0.5,
    "physical.lithography.gate_k1_resist_process_factor": 0.7,
    "physical.lithography.gate_k1_mask_error_factor": 1.2,
    "physical.lithography.gate_k1_resolution_enhancement_factor": 1.4,
}

IMPOSSIBLE_GATE_K1_PROCESS_FACTOR_CASES = [
    (
        "physical.lithography.gate_k1_aerial_image_contrast_factor",
        1.25,
        "domain.physical.lithography.gate_k1_aerial_image_contrast_factor.max",
    ),
    (
        "physical.lithography.gate_k1_resist_process_factor",
        0.0,
        "domain.physical.lithography.gate_k1_resist_process_factor.positive",
    ),
    (
        "physical.lithography.gate_k1_mask_error_factor",
        -0.1,
        "domain.physical.lithography.gate_k1_mask_error_factor.positive",
    ),
    (
        "physical.lithography.gate_k1_resolution_enhancement_factor",
        -0.5,
        (
            "domain."
            "physical.lithography.gate_k1_resolution_enhancement_factor"
            ".positive"
        ),
    ),
]


@contextlib.contextmanager
def captured_stdout():
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        yield buf
    finally:
        sys.stdout = old


def _assignments_with(variable_name, value):
    assignments = dict(VALID_GATE_K1_PROCESS_FACTOR_ASSIGNMENTS)
    assignments[variable_name] = value
    return assignments


def _failed_constraint(result, equation):
    check = next(c for c in result.constraints if c.equation == equation)
    assert check.satisfied is False
    assert check.missing == set()
    return check


@pytest.mark.parametrize(
    ("variable_name", "bad_value", "constraint"),
    IMPOSSIBLE_GATE_K1_PROCESS_FACTOR_CASES,
)
def test_resolver_reports_impossible_gate_k1_process_factor_assignments(
    variable_name,
    bad_value,
    constraint,
):
    result = resolve(
        "physical.lithography.gate_k1",
        assignments=_assignments_with(variable_name, bad_value),
    )

    _failed_constraint(result, constraint)


@pytest.mark.parametrize(
    ("variable_name", "bad_value", "constraint"),
    IMPOSSIBLE_GATE_K1_PROCESS_FACTOR_CASES,
)
def test_strict_invalid_gate_k1_process_factor_assignments_return_nonzero(
    variable_name,
    bad_value,
    constraint,
):
    assignment_args = []
    for name, value in _assignments_with(variable_name, bad_value).items():
        assignment_args.extend(["--assign", f"{name}={value}"])

    with captured_stdout() as buf:
        rc = main(
            [
                "resolve",
                "physical.lithography.gate_k1",
                *assignment_args,
                "--constraints",
                "--fail-on-violated-constraints",
            ]
        )

    assert rc == 1
    assert f"{constraint} [violated]" in buf.getvalue()
