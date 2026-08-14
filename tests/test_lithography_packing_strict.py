"""
tests/test_lithography_packing_strict.py
=========================================

The two packing knobs of the imaging medium have hard limits: the packing
length scale factor must be at least 1 (a formula unit cannot occupy a cell
smaller than its own separation), and the fill factor must be at most 1 (you
cannot fill more than all of the space). This module drives the CLI with a
value on the wrong side of each limit under --fail-on-violated-constraints
and checks the strict contract: exit code 1 and a "[violated]" line naming
the broken constraint, so shell scripts and CI can catch bad packing inputs.
"""

import contextlib
import io
import sys

import pytest

from gpu_stack.cli import main


@contextlib.contextmanager
def captured_stdout():
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        yield buf
    finally:
        sys.stdout = old


@pytest.mark.parametrize(
    ("target", "assignment", "constraint"),
    [
        (
            "physical.lithography.medium_formula_unit_packing_length_scale_factor",
            "physical.lithography.medium_formula_unit_packing_length_scale_factor=0.5",
            (
                "physical.ineq."
                "lithography_medium_formula_unit_packing_length_scale_factor_at_least_unity"
            ),
        ),
        (
            "physical.lithography.medium_formula_unit_packing_fill_factor",
            "physical.lithography.medium_formula_unit_packing_fill_factor=1.25",
            (
                "physical.ineq."
                "lithography_medium_formula_unit_packing_fill_factor_at_most_unity"
            ),
        ),
    ],
)
def test_strict_invalid_packing_constraints_return_nonzero(
    target,
    assignment,
    constraint,
):
    with captured_stdout() as buf:
        rc = main([
            "resolve",
            target,
            "--assign",
            assignment,
            "--constraints",
            "--fail-on-violated-constraints",
        ])

    assert rc == 1
    assert f"{constraint} [violated]" in buf.getvalue()
