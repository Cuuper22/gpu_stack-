"""CLI parser and registry smoke tests."""

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
