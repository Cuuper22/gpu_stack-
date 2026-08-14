"""Runs the demo end to end and checks it exits cleanly.

``python -m gpu_stack.demo`` is launched as a real subprocess, the same way
a user runs it. The demo touches graph health, topological sort, and
symbolic substitution in one pass, so this single test catches integration
breakage — a bad import, a cycle, a crash on startup — that narrower unit
tests can miss.
"""

import subprocess
import sys


def test_demo_runs_cleanly():
    result = subprocess.run(
        [sys.executable, "-m", "gpu_stack.demo"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        "demo exit code "
        f"{result.returncode}; stderr: {result.stderr}"
    )
    assert "cycles" in result.stdout.lower() or result.stdout.strip() != ""
