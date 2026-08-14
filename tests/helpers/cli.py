"""Helpers for CLI tests: capture printed output and pick apart scenario reports.

The CLI writes to stdout and stderr, so tests need a way to grab that text.
Scenario runs return lists of report dicts, so tests also need small selectors
that find one report or one target by name and fail with a clear message when
it is missing.
"""

from __future__ import annotations

import contextlib
import io
import sys

from tests.helpers.registry import snapshot_registry_state as registry_snapshot


ORIGINAL_PYTHIA_SCENARIO = "pythia_70m_dgx_h100_us_2024_industrial_power"
# The canonical energy-floor pack name. Use an exact-name match to stay
# stable when more energy-floor variants are added.
PYTHIA_ENERGY_FLOOR_SCENARIO_NAME = (
    "pythia_70m_dgx_h100_us_2024_industrial_energy_floor_cost"
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
        if report["preset"] == PYTHIA_ENERGY_FLOOR_SCENARIO_NAME
    ]
    assert len(candidates) == 1, (
        f"expected exactly one report for {PYTHIA_ENERGY_FLOOR_SCENARIO_NAME!r}; got "
        f"{sorted(report['preset'] for report in reports)}"
    )
    return candidates[0]
