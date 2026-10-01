"""Imports every physical scope module in a clean subprocess.

Each module is imported in a fresh Python process, with no cached modules and
no import-order luck, so a circular import or a missing name fails loudly
with the subprocess's own traceback.
"""

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCOPES_DIR = REPO_ROOT / "gpu_stack" / "scopes"
SCOPES_PACKAGE = "gpu_stack.scopes"

REQUIRED_ANCHORS = {
    f"{SCOPES_PACKAGE}.physical_interconnect",
    f"{SCOPES_PACKAGE}.physical_lithography",
    f"{SCOPES_PACKAGE}.physical_mosfet",
    f"{SCOPES_PACKAGE}.physical_process",
}


def physical_scope_modules() -> list[str]:
    return sorted(
        f"{SCOPES_PACKAGE}.{path.stem}"
        for path in SCOPES_DIR.glob("physical_*.py")
    )


def test_physical_scopes_import_in_clean_process():
    modules = physical_scope_modules()
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
        "Physical scope imports failed.\n"
        f"Modules: {modules}\n"
        f"stdout:\n{completed.stdout}\n"
        f"stderr:\n{completed.stderr}"
    )
