"""Smoke tests for the CLI entry point.

Two cheap checks that catch total breakage fast: the argument parser builds
at all (its program name is ``gpu-stack``), and the ``stats`` command runs
and prints the published registry variable count. If either fails, every
other CLI test will fail too, and these point to the root cause first.
"""

from gpu_stack.cli import build_parser, main
from tests.helpers.cli import captured_stdout
from tests.test_import_registry import PUBLISHED_SNAPSHOT


def test_parser_builds_without_args():
    parser = build_parser()
    assert parser.prog == "gpu-stack"


def test_stats_prints_registry_counts():
    with captured_stdout() as buf:
        rc = main(["stats"])
    out = buf.getvalue()
    assert rc == 0
    assert "variables" in out
    assert str(PUBLISHED_SNAPSHOT["variables"]) in out
    assert "Coverage" in out
