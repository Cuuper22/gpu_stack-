"""
tests/test_cli_physical_boundary_smoke.py
=========================================

Fast CLI smoke coverage for invalid physical-boundary assignments.
"""

from __future__ import annotations

import contextlib
import io

import pytest

from gpu_stack.cli import main


PHYSICAL_BOUNDARY_SMOKE_CASES = (
    pytest.param(
        "physical.mosfet.channel_parallel_count",
        "0",
        "physical.ineq.mosfet_channel_parallel_count_at_least_one",
        id="mosfet-channel-count",
    ),
    pytest.param(
        "physical.interconnect.route_detour_factor",
        "0.5",
        "physical.ineq.interconnect_route_detour_factor_at_least_unity",
        id="interconnect-detour",
    ),
    pytest.param(
        "physical.process.drawn_gate_length",
        "0",
        "physical.ineq.drawn_gate_length_positive",
        id="process-drawn-gate",
    ),
    pytest.param(
        "physical.lithography.source_plasma_species_partial_pressure",
        "0",
        "physical.ineq.lithography_source_plasma_species_partial_pressure_positive",
        id="lithography-plasma-pressure",
    ),
)


def _run_resolve_with_bad_assignment(target: str, value: str) -> tuple[int, str]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = main(
            [
                "resolve",
                target,
                "--assign",
                f"{target}={value}",
                "--constraints",
                "--fail-on-violated-constraints",
            ]
        )
    return rc, buf.getvalue()


@pytest.mark.parametrize(
    ("target", "bad_value", "violated_constraint"),
    PHYSICAL_BOUNDARY_SMOKE_CASES,
)
def test_cli_rejects_invalid_physical_boundary_assignments(
    target: str,
    bad_value: str,
    violated_constraint: str,
):
    rc, out = _run_resolve_with_bad_assignment(target, bad_value)

    assert rc == 1
    assert f"{target} =" in out
    assert "constraints:" in out
    assert f"{violated_constraint} [violated]" in out
