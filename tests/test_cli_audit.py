"""Tests for the ``audit`` CLI command, the model's own health check.

``audit`` scans the registry for integrity problems: equations that
collapsed to a trivial identity, raw SymPy symbols with no registered
variable behind them, orphan value equations, and source files grown past
the size threshold. These tests verify a clean model audits clean, that the
report names each counter, and that deliberately planted defects flip the
exit code to 1 and appear in the details.
"""

import sympy as sp

import gpu_stack.cli as cli_mod
from gpu_stack import Registry
from gpu_stack.cli import main
from gpu_stack.core import Inequality, var
from tests.helpers.cli import captured_stdout, registry_snapshot


def test_audit_reports_integrity_counts():
    with captured_stdout() as buf:
        rc = main(["audit", "--fail-on-issues"])
    out = buf.getvalue()
    assert rc == 0
    assert "Audit:" in out
    assert "collapsed_equations             0" in out
    assert "collapsed_approximation_validity 0" in out
    assert "unresolved_raw_symbols          0" in out
    assert "orphan_value_equations          0" in out
    assert "large_scope_files               0" in out
    assert "large_project_files" in out
    assert "hard_failures                   0" in out


def test_audit_large_project_files_scan_core_and_tests_after_cli_split():
    large_files = {
        name for name, _lines in cli_mod._large_project_files(threshold=700)
    }

    assert not any(name.startswith("gpu_stack/cli") for name in large_files)
    assert "gpu_stack/core/equation.py" not in large_files
    # The CLI tests were split into shards precisely to get under the
    # large-file audit threshold; no shard may grow back past it.
    assert not any(name.startswith("tests/test_cli") for name in large_files)
    assert not any(
        name.startswith("tests/test_process_geometry") for name in large_files
    )


def test_audit_details_lists_multi_definition_variables():
    with captured_stdout() as buf:
        rc = main(["audit", "--details"])
    out = buf.getvalue()
    assert rc == 0
    assert "multi_definition_variables" in out
    assert "training.flops_per_step" in out


def test_audit_fails_on_raw_symbol_in_expression_lhs_constraint():
    with registry_snapshot():
        owner = var(
            "test.cli.raw_lhs.owner",
            "test_cli_raw_lhs_owner",
            "value",
            "Temporary CLI raw-LHS owner.",
            scope="test",
        )
        raw = sp.Symbol("test_cli_raw_lhs_ghost")
        Inequality(
            "test.cli.ineq.raw_lhs",
            owner.symbol + raw,
            0,
            "<=",
            "Temporary CLI raw-LHS constraint.",
        )

        with captured_stdout() as buf:
            rc = main(["audit", "--details", "--fail-on-issues"])

    out = buf.getvalue()
    assert rc == 1
    assert "unresolved_raw_symbols          1" in out
    assert "test.cli.ineq.raw_lhs: test_cli_raw_lhs_ghost" in out


def test_audit_fails_on_collapsed_approximation_validity():
    with registry_snapshot():
        equation = Registry.equations[
            "physical.eq.lithography_source_nuclear_radius_coefficient"
        ]
        original_validity = equation.validity
        try:
            equation.validity = sp.S.true

            with captured_stdout() as buf:
                rc = main(["audit", "--details", "--fail-on-issues"])
        finally:
            equation.validity = original_validity

    out = buf.getvalue()
    assert rc == 1
    assert "collapsed_approximation_validity 1" in out
    assert "physical.eq.lithography_source_nuclear_radius_coefficient" in out
