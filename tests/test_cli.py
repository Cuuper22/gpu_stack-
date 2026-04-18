"""
tests/test_cli.py
=================

CLI smoke tests. The CLI is a thin wrapper over the registry, the
resolver, and the preset library; these tests verify the wiring, not
the underlying math.
"""

import io
import sys
import contextlib

import pytest

from gpu_stack.cli import build_parser, main


@contextlib.contextmanager
def captured_stdout():
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        yield buf
    finally:
        sys.stdout = old


def test_parser_builds_without_args():
    parser = build_parser()
    assert parser.prog == "gpu-stack"


def test_stats_prints_registry_counts():
    with captured_stdout() as buf:
        rc = main(["stats"])
    out = buf.getvalue()
    assert rc == 0
    assert "variables" in out
    assert "1147" in out
    assert "Coverage" in out


def test_list_presets_shows_demo_rack():
    with captured_stdout() as buf:
        rc = main(["list-presets"])
    out = buf.getvalue()
    assert rc == 0
    assert "hardware.demo_rack" in out
    assert "workload.dense_variant_selector" in out


def test_resolve_with_preset_hits_demo_number():
    with captured_stdout() as buf:
        rc = main([
            "resolve",
            "cluster.rack.peak_flops",
            "--preset", "hardware.demo_rack",
        ])
    out = buf.getvalue()
    assert rc == 0
    assert "cluster.rack.peak_flops" in out
    # 1.08e18 shown in SymPy Float format.
    assert "1.08" in out


def test_resolve_with_inline_assignment():
    with captured_stdout() as buf:
        rc = main([
            "resolve",
            "cluster.node.peak_flops",
            "--assign", "cluster.node.n_gpus=4",
            "--assign", "gpu.peak_flops=2e15",
        ])
    out = buf.getvalue()
    assert rc == 0
    assert "8.00" in out.replace("E+", "e+").replace("E-", "e-")


def test_resolve_trace_prints_equation_names():
    with captured_stdout() as buf:
        rc = main([
            "resolve",
            "cluster.rack.peak_flops",
            "--preset", "hardware.demo_rack",
            "--trace",
        ])
    out = buf.getvalue()
    assert rc == 0
    assert "cluster.eq.rack_peak_flops" in out


def test_resolve_unknown_preset_raises_clean_error():
    with pytest.raises(SystemExit):
        main([
            "resolve",
            "cluster.rack.peak_flops",
            "--preset", "hardware.does_not_exist",
        ])
