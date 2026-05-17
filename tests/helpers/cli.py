"""CLI test helpers and scenario-report selectors."""

from __future__ import annotations

import contextlib
import io
import sys

from tests.helpers.registry import snapshot_registry_state as registry_snapshot


ORIGINAL_PYTHIA_SCENARIO = "pythia_70m_dgx_h100_us_2024_industrial_power"
PYTHIA_ENERGY_FLOOR_SCENARIO_MARKERS = (
    "pythia_70m",
    "dgx_h100",
    "energy_floor",
)


@contextlib.contextmanager
def captured_stdout():
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        yield buf
    finally:
        sys.stdout = old


@contextlib.contextmanager
def captured_stderr():
    buf = io.StringIO()
    old = sys.stderr
    sys.stderr = buf
    try:
        yield buf
    finally:
        sys.stderr = old


def unresolved_input_line(out: str, variable: str) -> str:
    needle = f"  {variable} "
    for line in out.splitlines():
        if line.startswith(needle):
            return line.strip()
    raise AssertionError(f"missing unresolved-input line for {variable}")


def report_by_preset(reports, preset_name: str):
    try:
        return next(report for report in reports if report["preset"] == preset_name)
    except StopIteration:
        names = sorted(report["preset"] for report in reports)
        raise AssertionError(f"missing scenario report {preset_name!r}; got {names}")


def target_by_label(report, label: str):
    try:
        return next(target for target in report["targets"] if target["label"] == label)
    except StopIteration:
        labels = [target["label"] for target in report["targets"]]
        raise AssertionError(
            f"missing target {label!r} for {report['preset']!r}; got {labels}"
        )


def pythia_energy_floor_report(reports):
    candidates = [
        report
        for report in reports
        if all(
            marker in report["preset"].replace("-", "_").lower()
            for marker in PYTHIA_ENERGY_FLOOR_SCENARIO_MARKERS
        )
    ]
    assert len(candidates) == 1, (
        "expected one sourced Pythia/DGX H100 energy-floor scenario; got "
        f"{sorted(report['preset'] for report in reports)}"
    )
    return candidates[0]
