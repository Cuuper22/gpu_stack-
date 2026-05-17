"""Formatting helpers for next-work evidence."""

from __future__ import annotations

from typing import Iterable

from .next_work_evidence import _RootDebtFamily, _RootDebtRow


def _missing_family_summary(target: object | None, limit: int = 4) -> str:
    if target is None:
        return "no target report found"
    summaries = tuple(getattr(target, "missing_family_summaries", ()))
    if not summaries:
        return "missing families: none"
    parts = [
        (
            f"{summary.family} {summary.boundary_category} "
            f"primitive={summary.primitive_boundary} count={summary.count}"
        )
        for summary in summaries[:limit]
    ]
    remaining = len(summaries) - len(parts)
    if remaining > 0:
        parts.append(f"{remaining} more families")
    return "missing families: " + "; ".join(parts)


def _format_roots(roots: Iterable[_RootDebtRow], limit: int = 4) -> str:
    selected = tuple(roots)[:limit]
    return ", ".join(f"{root.name}:{root.dependents}" for root in selected)


def _format_families(families: Iterable[_RootDebtFamily]) -> str:
    return "; ".join(
        f"{family.family} weight={family.total_weight} roots={family.root_count}"
        for family in families
    )


def _format_labels(labels: Iterable[str]) -> str:
    selected = tuple(labels)
    return ", ".join(selected) if selected else "none"


def _format_large_files(files: Iterable[tuple[str, int]], limit: int = 4) -> str:
    all_files = tuple(files)
    selected = all_files[:limit]
    if not selected:
        return "none"
    rendered = ", ".join(f"{path}:{lines}" for path, lines in selected)
    remaining = len(all_files) - len(selected)
    if remaining > 0:
        rendered = f"{rendered}, {remaining} more"
    return rendered
