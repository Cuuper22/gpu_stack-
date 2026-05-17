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
    """Exactly three top-level next-work lists."""

    highest_impact: tuple[NextWorkItem, ...]
    best_implementations: tuple[NextWorkItem, ...]
    bug_risks: tuple[NextWorkItem, ...]
    graph_evidence: Mapping[str, int]

    @property
    def implementation(self) -> tuple[NextWorkItem, ...]:
        """Compatibility alias for continuation-contract callers."""
        return self.best_implementations

    def to_dict(self) -> dict[str, list[dict[str, str]]]:
        return {
            "highest_impact": [item.to_dict() for item in self.highest_impact],
            "best_implementations": [
                item.to_dict() for item in self.best_implementations
            ],
            "bug_risks": [item.to_dict() for item in self.bug_risks],
        }
