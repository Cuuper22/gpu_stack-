"""
tests/test_mosfet_constraints.py
================================

The MOSFET model has two layers of guard rails. Domain assumptions live on
the variables themselves: widths, oxide thicknesses, and capacitances must
be positive, the parallel channel count must be a nonnegative integer, and
the gate-tunneling terms nonnegative. Named feasibility inequalities add
the physics that assumptions cannot express: a transistor needs at least
one channel, its total width must come out positive after the width bias,
the ideality factor is at least 1, and the subthreshold swing can never
drop below its thermodynamic floor of ~60 mV/decade at room temperature
(here expressed against the swing-floor variable). This module verifies
both layers exist with the right operators and bounds, feeds impossible
assignments through resolve to confirm each violation is reported, and
runs one case through the CLI to check strict mode prints the violated
constraint and exits 1.
"""

import contextlib
import io
import sys

import pytest
import sympy as sp

from gpu_stack import Registry, resolve
from gpu_stack.cli import main
from gpu_stack.core import domain_relations_for_variable


@contextlib.contextmanager
def captured_stdout():
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        yield buf
    finally:
        sys.stdout = old


def _domain_suffixes(variable_name):
    return {
        suffix
        for suffix, _relation in domain_relations_for_variable(
            Registry.variables[variable_name]
        )
    }


def _failed_constraint(result, equation):
    check = next(c for c in result.constraints if c.equation == equation)
    assert check.satisfied is False
    assert check.missing == set()
    assert any(v.equation == equation for v in result.violated_constraints)
    return check


def test_mosfet_clear_domain_constraints_exist():
    expected_domains = {
        "physical.mosfet.width": {"positive"},
        "physical.mosfet.channel_parallel_count": {"integer", "nonnegative"},
        "physical.mosfet.channel_unit_width": {"positive"},
        "physical.mosfet.oxide_thickness": {"positive"},
        "physical.mosfet.eot": {"positive"},
        "physical.mosfet.sio2_relative_permittivity": {"positive"},
        "physical.mosfet.oxide_relative_permittivity": {"positive"},
        "physical.mosfet.oxide_permittivity": {"positive"},
        "physical.mosfet.c_ox": {"positive"},
        "physical.mosfet.subthreshold_swing_floor": {"positive"},
        "physical.mosfet.subthreshold_swing": {"positive"},
        "physical.mosfet.channel_length_modulation": {"nonnegative"},
        "physical.mosfet.ideality": {"positive"},
        "physical.mosfet.gate_tunnel_prefactor": {"nonnegative"},
        "physical.mosfet.gate_tunnel_decay": {"nonnegative"},
        "physical.mosfet.gate_tunnel_current_density": {"nonnegative"},
    }

    for variable_name, expected in expected_domains.items():
        assert expected <= _domain_suffixes(variable_name)


def test_mosfet_explicit_feasibility_constraints_exist():
    expected_constraints = [
        (
            "physical.mosfet.channel_parallel_count",
            "physical.ineq.mosfet_channel_parallel_count_at_least_one",
            ">=",
            sp.Integer(1),
        ),
        (
            "physical.mosfet.width",
            "physical.ineq.mosfet_channel_width_positive",
            ">",
            sp.Integer(0),
        ),
        (
            "physical.mosfet.ideality",
            "physical.ineq.mosfet_ideality_at_least_one",
            ">=",
            sp.Integer(1),
        ),
        (
            "physical.mosfet.subthreshold_swing",
            "physical.eq.subthreshold_swing_floor_constraint",
            ">=",
            Registry.variables["physical.mosfet.subthreshold_swing_floor"].symbol,
        ),
    ]

    for variable_name, equation_name, op, rhs in expected_constraints:
        relation = Registry.equations[equation_name]
        assert relation in Registry.variables[variable_name].constraints()
        assert relation.op == op
        assert relation.rhs == rhs
        assert relation in Registry.systems["physical"].equations


@pytest.mark.parametrize(
    ("target", "assignments", "constraint"),
    [
        (
            "physical.mosfet.width",
            {
                "physical.mosfet.channel_parallel_count": 0,
                "physical.mosfet.channel_unit_width": 2.0,
                "physical.mosfet.channel_width_bias": 1.0,
            },
            "physical.ineq.mosfet_channel_parallel_count_at_least_one",
        ),
        (
            "physical.mosfet.width",
            {
                "physical.mosfet.channel_parallel_count": 1,
                "physical.mosfet.channel_unit_width": 1.0,
                "physical.mosfet.channel_width_bias": -2.0,
            },
            "physical.ineq.mosfet_channel_width_positive",
        ),
        (
            "physical.mosfet.subthreshold_swing",
            {
                "physical.mosfet.ideality": 0.5,
                "physical.temperature": 300.0,
            },
            "physical.ineq.mosfet_ideality_at_least_one",
        ),
        (
            "physical.mosfet.gate_tunnel_current_density",
            {
                "physical.mosfet.gate_tunnel_prefactor": -1.0,
                "physical.mosfet.gate_tunnel_decay": 0.0,
                "physical.mosfet.oxide_thickness": 1.0,
            },
            "domain.physical.mosfet.gate_tunnel_prefactor.nonnegative",
        ),
    ],
)
def test_resolver_reports_impossible_mosfet_boundary_assignments(
    target,
    assignments,
    constraint,
):
    result = resolve(target, assignments=assignments)

    _failed_constraint(result, constraint)


def test_cli_strict_reports_impossible_mosfet_boundary_assignment():
    with captured_stdout() as buf:
        rc = main([
            "resolve",
            "physical.mosfet.width",
            "--assign", "physical.mosfet.channel_parallel_count=0",
            "--assign", "physical.mosfet.channel_unit_width=2.0",
            "--assign", "physical.mosfet.channel_width_bias=1.0",
            "--constraints",
            "--fail-on-violated-constraints",
        ])

    assert rc == 1
    assert (
        "physical.ineq.mosfet_channel_parallel_count_at_least_one [violated]"
        in buf.getvalue()
    )
