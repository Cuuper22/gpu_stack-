"""Public data models for live next-work planning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class NextWorkItem:
    """One actionable next-work item backed by concrete current evidence."""

    title: str
    evidence: str
    command: str | None = None
    path: str | None = None

    def to_dict(self) -> dict[str, str]:
        data = {
            "title": self.title,
            "evidence": self.evidence,
        }
        if self.command is not None:
            data["command"] = self.command
        if self.path is not None:
            data["path"] = self.path
        return data


@dataclass(frozen=True)
class NextWorkPlan:
    """Research-first next-work plan with compatibility diagnostics.

    ``highest_impact`` remains the stable public name used by existing API and
    JSON consumers.  It now contains scientific research priorities.  Legacy
    root-debt and scenario-closure diagnostics are carried separately so they
    remain available without being mistaken for the research objective.
    """

    highest_impact: tuple[NextWorkItem, ...]
    best_implementations: tuple[NextWorkItem, ...]
    bug_risks: tuple[NextWorkItem, ...]
    graph_evidence: Mapping[str, int]
    legacy_diagnostics: tuple[NextWorkItem, ...] = ()

    @property
    def research_priorities(self) -> tuple[NextWorkItem, ...]:
        """Explicit research-oriented alias for ``highest_impact``."""
        return self.highest_impact

    @property
    def implementation(self) -> tuple[NextWorkItem, ...]:
        """Compatibility alias for continuation-contract callers."""
        return self.best_implementations

    def to_dict(self) -> dict[str, list[dict[str, str]]]:
        """Return the established three-section JSON wire shape.

        ``research_priorities`` and ``legacy_diagnostics`` are intentionally
        properties of the Python plan rather than new default JSON keys.  This
        lets existing command consumers keep parsing the same payload while
        the meaning of ``highest_impact`` advances from root closure to
        scientific leverage.
        """
        return {
            "highest_impact": [item.to_dict() for item in self.highest_impact],
            "best_implementations": [
                item.to_dict() for item in self.best_implementations
            ],
            "bug_risks": [item.to_dict() for item in self.bug_risks],
        }
