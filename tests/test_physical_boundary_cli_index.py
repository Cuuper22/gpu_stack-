"""Index test for physical-boundary CLI and strict-mode coverage.

Some guarantees live not in one test but in a set of tests spread across
modules: the CLI rejects invalid physical-boundary assignments, strict mode
returns a nonzero exit code, boundary constraints are registered once, and
so on. If one of those tests is renamed or deleted, the guarantee silently
vanishes while the suite stays green.

This module is the guard against that. It keeps an explicit map from module
name to the test functions that must exist there, imports each module, and
fails with the missing names if any indexed test has disappeared.
"""

from __future__ import annotations

import importlib
import inspect


EXPECTED_PHYSICAL_BOUNDARY_COVERAGE = {
    "tests.test_cli_physical_boundary_smoke": {
        "test_cli_rejects_invalid_physical_boundary_assignments",
    },
    "tests.test_lithography_k1_strict": {
        "test_resolver_reports_impossible_gate_k1_process_factor_assignments",
        "test_strict_invalid_gate_k1_process_factor_assignments_return_nonzero",
    },
    "tests.test_lithography_packing_strict": {
        "test_strict_invalid_packing_constraints_return_nonzero",
    },
    "tests.test_physical_process_boundaries": {
        "test_invalid_process_boundary_assignments_report_single_diagnostic",
        "test_process_boundary_constraints_are_registered_once",
    },
    "tests.test_root_debt_physical_boundaries": {
        "test_physical_boundary_hardening_constraints_are_graph_constraints",
        "test_physical_boundary_hardening_is_visible_in_root_debt_rows",
    },
}


def test_physical_boundary_cli_and_strict_mode_coverage_is_indexed():
    for module_name, expected_functions in EXPECTED_PHYSICAL_BOUNDARY_COVERAGE.items():
        module = importlib.import_module(module_name)
        discovered_functions = {
            name
            for name, obj in inspect.getmembers(module, inspect.isfunction)
            if inspect.getmodule(obj) is module
        }

        missing = expected_functions - discovered_functions

        assert not missing, f"{module_name} is missing indexed tests: {sorted(missing)}"
