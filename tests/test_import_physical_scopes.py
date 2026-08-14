"""Imports the high-churn physical scope modules in a clean subprocess.

The lithography plasma, species, medium, and nuclear modules change often,
and an import error there can hide inside a test session that already
loaded half the package. This test imports each module in a fresh Python
process — no cached modules, no import order luck — so a circular import
or a missing name fails loudly with the subprocess's own traceback.
"""

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCOPES_DIR = REPO_ROOT / "gpu_stack" / "scopes"
SCOPES_PACKAGE = "gpu_stack.scopes"

BASE_PHYSICAL_MODULES = {
    f"{SCOPES_PACKAGE}.physical_interconnect",
    f"{SCOPES_PACKAGE}.physical_mosfet",
    f"{SCOPES_PACKAGE}.physical_process",
}

LITHOGRAPHY_FAMILIES = ("plasma", "species", "medium", "nuclear")
REQUIRED_ANCHORS = BASE_PHYSICAL_MODULES | {
    f"{SCOPES_PACKAGE}.physical_lithography_medium_response",
    f"{SCOPES_PACKAGE}.physical_lithography_nuclear_binding_coefficients",
    f"{SCOPES_PACKAGE}.physical_lithography_plasma_state",
    f"{SCOPES_PACKAGE}.physical_lithography_species",
}


def focused_physical_scope_modules() -> list[str]:
    lithography_modules = {
        f"{SCOPES_PACKAGE}.{path.stem}"
        for path in SCOPES_DIR.glob("physical_lithography_*.py")
        if any(family in path.stem for family in LITHOGRAPHY_FAMILIES)
    }
    return sorted(BASE_PHYSICAL_MODULES | lithography_modules)


def test_high_churn_physical_scopes_import_in_clean_process():
    modules = focused_physical_scope_modules()
    missing_anchors = REQUIRED_ANCHORS - set(modules)
    assert missing_anchors == set()

    script = """
import importlib
import json
import sys

for module_name in json.loads(sys.argv[1]):
    importlib.import_module(module_name)
"""
    completed = subprocess.run(
        [sys.executable, "-c", script, json.dumps(modules)],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert completed.returncode == 0, (
        "Focused physical scope imports failed.\n"
        f"Modules: {modules}\n"
        f"stdout:\n{completed.stdout}\n"
        f"stderr:\n{completed.stderr}"
    )
