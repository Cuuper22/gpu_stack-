"""
Report artifacts produced when a Preset evaluates its targets.

A ScenarioReport wraps one ScenarioTargetReport per evaluated target, plus
summaries of unresolved inputs grouped by family. All three dataclasses
are frozen and JSON-friendly on purpose: reports get serialized, diffed,
and asserted on. They live outside ``core.presets`` so the Preset class
can focus on validation and resolver orchestration, not bookkeeping.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

from .resolver import UnresolvedInput


@dataclass(frozen=True)
class MissingFamilySummary:
    """Stable summary of unresolved inputs grouped by resolver family."""

    family: str
    boundary_category: str
    primitive_boundary: bool
    count: int
    names: Tuple[str, ...]

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ScenarioTargetReport:
    """Structured, JSON-friendly evaluation artifact for one target."""

    label: str
    target: str
    status: str
    issue_count: int
    value: Optional[str] = None
    missing_count: int = 0
    missing_names: Tuple[str, ...] = ()
    unresolved_inputs: Tuple[UnresolvedInput, ...] = ()
    missing_family_summaries: Tuple[MissingFamilySummary, ...] = ()
    violated_constraint_count: int = 0
    violated_constraint_equations: Tuple[str, ...] = ()
    violated_approximation_validity_count: int = 0
    violated_approximation_validity_equations: Tuple[str, ...] = ()
    trace_step_count: int = 0
    trace_equation_count: int = 0
    trace_equations: Tuple[str, ...] = ()
    error_type: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        data = asdict(self)
        data["trace_steps"] = self.trace_step_count
        data["trace_equation_count"] = self.trace_equation_count
        return data


@dataclass(frozen=True)
class ScenarioReport:
    """Structured evaluation artifact for a preset across many targets."""

    preset_name: str
    preset_description: str
    has_source: bool
    source: Optional[str]
    assignment_count: int
    variant_count: int
    target_count: int
    status: str
    issue_count: int
    targets: Tuple[ScenarioTargetReport, ...]
    ok_count: int = field(init=False)
    issues_count: int = field(init=False)
    error_count: int = field(init=False)
    target_labels: Tuple[str, ...] = field(init=False)
    ok_target_labels: Tuple[str, ...] = field(init=False)
    issue_target_labels: Tuple[str, ...] = field(init=False)
    error_target_labels: Tuple[str, ...] = field(init=False)
    missing_family_summaries: Tuple[MissingFamilySummary, ...] = field(init=False)

    def __post_init__(self) -> None:
        target_labels = tuple(target.label for target in self.targets)
        ok_target_labels = tuple(
            target.label for target in self.targets
            if target.status == "ok"
        )
        issue_target_labels = tuple(
            target.label for target in self.targets
            if target.issue_count > 0
        )
        error_target_labels = tuple(
            target.label for target in self.targets
            if target.status == "error"
        )
        unresolved_inputs = tuple(
            unresolved
            for target in self.targets
            for unresolved in target.unresolved_inputs
        )

        object.__setattr__(self, "ok_count", len(ok_target_labels))
        # issue_count is the individual issue total; issues_count is target-level.
        object.__setattr__(self, "issues_count", len(issue_target_labels))
        object.__setattr__(self, "error_count", len(error_target_labels))
        object.__setattr__(self, "target_labels", target_labels)
        object.__setattr__(self, "ok_target_labels", ok_target_labels)
        object.__setattr__(self, "issue_target_labels", issue_target_labels)
        object.__setattr__(self, "error_target_labels", error_target_labels)
        object.__setattr__(
            self,
            "missing_family_summaries",
            _missing_family_summaries(_dedupe_unresolved_inputs(unresolved_inputs)),
        )

    def to_dict(self) -> Dict[str, object]:
        return {
            "preset": self.preset_name,
            "preset_name": self.preset_name,
            "description": self.preset_description,
            "sourced": self.has_source,
            "has_source": self.has_source,
            "source": self.source,
            "assignment_count": self.assignment_count,
            "variant_count": self.variant_count,
            "target_count": self.target_count,
            "status": self.status,
            "issue_count": self.issue_count,
            "ok_count": self.ok_count,
            "issues_count": self.issues_count,
            "error_count": self.error_count,
            "target_labels": self.target_labels,
            "ok_target_labels": self.ok_target_labels,
            "issue_target_labels": self.issue_target_labels,
            "error_target_labels": self.error_target_labels,
            "missing_family_summaries": tuple(
                summary.to_dict()
                for summary in self.missing_family_summaries
            ),
            "targets": {
                target.label: target.to_dict()
                for target in self.targets
            },
        }


def _missing_family_summaries(
    unresolved_inputs: Iterable[UnresolvedInput],
) -> Tuple[MissingFamilySummary, ...]:
    by_family: Dict[Tuple[str, str, bool], List[str]] = {}
    for item in unresolved_inputs:
        family = item.family or "unknown"
        key = (
            family,
            item.boundary_category or "unknown",
            bool(item.primitive_boundary),
        )
        by_family.setdefault(key, []).append(item.variable)
    return tuple(
        MissingFamilySummary(
            family=family,
            boundary_category=boundary_category,
            primitive_boundary=primitive_boundary,
            count=len(names),
            names=tuple(sorted(names)),
        )
        for (
            family,
            boundary_category,
            primitive_boundary,
        ), names in sorted(by_family.items())
    )


def _dedupe_unresolved_inputs(
    unresolved_inputs: Iterable[UnresolvedInput],
) -> Tuple[UnresolvedInput, ...]:
    by_variable: Dict[str, UnresolvedInput] = {}
    for item in unresolved_inputs:
        by_variable.setdefault(item.variable, item)
    return tuple(by_variable.values())


__all__ = [
    "MissingFamilySummary",
    "ScenarioReport",
    "ScenarioTargetReport",
]
