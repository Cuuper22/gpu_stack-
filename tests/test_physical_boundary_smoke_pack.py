"""Import smoke test for the physical-boundary smoke pack.

The smoke pack is the small set of test modules we run first to catch broken
imports before the full suite spends time collecting. This test simply imports
each module in the pack. Required modules must import; the two index modules
are optional — if they exist they must import cleanly, but their absence is
not an error, since they can be trimmed independently of the core pack.
"""

import importlib
import importlib.util


REQUIRED_SMOKE_MODULES = (
    "tests.test_import_physical_scopes",
    "tests.test_cli_physical_boundary_smoke",
    "tests.test_root_debt_physical_boundaries",
)

OPTIONAL_SMOKE_MODULES = (
    "tests.test_physical_boundary_test_index",
    "tests.test_physical_boundary_cli_index",
)


def test_physical_boundary_smoke_pack_imports_cleanly():
    for module_name in REQUIRED_SMOKE_MODULES:
        importlib.import_module(module_name)

    for module_name in OPTIONAL_SMOKE_MODULES:
        if importlib.util.find_spec(module_name) is not None:
            importlib.import_module(module_name)
