"""
Live next-work planning from the current registry and preset evidence.

This module intentionally builds its output at call time. The registry, preset
inventory, scenario targets, and source files are moving quickly, so a static
snapshot would go stale almost immediately.
"""

from __future__ import annotations

from pathlib import Path

from .next_work_evidence import (
    _Evidence,
    _RootDebtFamily,
    _RootDebtRow,
    _collect_evidence,
    _large_project_files,
    _root_debt_families,
    _target_by_label,
)
from .next_work_models import NextWorkItem, NextWorkPlan
from .next_work_rendering import (
    _format_families,
    _format_labels,
    _format_large_files,
    _format_roots,
    _missing_family_summary,
)
from .next_work_reports import (
    _best_implementations,
    _bug_risks,
    _highest_impact,
)


def build_next_work_plan(repo_root: Path | None = None) -> NextWorkPlan:
    """
    Build a live next-work plan from the currently imported registry.

    The returned plan has exactly three top-level lists:
    ``highest_impact`` with 3 items, ``best_implementations`` with 4 items,
    and ``bug_risks`` with 10 items.
    """

    evidence = _collect_evidence(repo_root)
    return NextWorkPlan(
        highest_impact=_highest_impact(evidence),
        best_implementations=_best_implementations(evidence),
        bug_risks=_bug_risks(evidence),
        graph_evidence={
            "variables": evidence.stats["variables"],
            "equations": evidence.stats["equations"],
            "root_inputs": evidence.stats["root_inputs"],
        },
    )


__all__ = [
    "NextWorkItem",
    "NextWorkPlan",
    "build_next_work_plan",
]
