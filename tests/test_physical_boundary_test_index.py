"""Index test for the focused physical-boundary test modules.

Seven test modules were added or expanded together to cover physical boundary
constraints (lithography media, plasma sources, nuclear binding, process
geometry, root debt). This index makes sure the set stays whole: each module
must exist as a file in this directory, be importable under its dotted name,
resolve to that exact file, and define at least one test function.

We check names and importability only — never the suite's total collection
count — so unrelated test churn cannot break this index.
"""

from importlib import import_module
from importlib.util import find_spec
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent

PHYSICAL_BOUNDARY_TEST_MODULES = (
    "tests.test_lithography_medium_intercomponent_boundaries",
    "tests.test_lithography_medium_response_boundaries",
    "tests.test_lithography_nuclear_binding_boundaries",
    "tests.test_lithography_source_plasma_drive_boundaries",
    "tests.test_lithography_source_species_boundaries",
    "tests.test_physical_process_boundaries",
    "tests.test_root_debt_physical_boundaries",
)


def test_focused_physical_boundary_test_modules_are_present_by_name():
    missing = []

    for module_name in PHYSICAL_BOUNDARY_TEST_MODULES:
        module_file = TESTS_DIR / f"{module_name.rsplit('.', maxsplit=1)[-1]}.py"
        spec = find_spec(module_name)
        if spec is None or not module_file.is_file():
            missing.append(module_name)
            continue

        assert Path(spec.origin).resolve() == module_file.resolve()

    assert missing == []


def test_focused_physical_boundary_test_modules_import_cleanly():
    modules_without_tests = []

    for module_name in PHYSICAL_BOUNDARY_TEST_MODULES:
        module = import_module(module_name)
        test_names = [
            name
            for name, value in vars(module).items()
            if name.startswith("test_") and callable(value)
        ]
        if not test_names:
            modules_without_tests.append(module_name)

    assert modules_without_tests == []
