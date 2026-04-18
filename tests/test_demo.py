"""
tests/test_demo.py
==================

Run the demo as a subprocess to confirm `python -m gpu_stack.demo` exits
cleanly. The demo also exercises graph health, topological sort, and
symbolic substitution, so a failure here catches integration regressions
that the other smoke tests may not surface.
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
