"""
core/presets.py
===============

Scenario-preset framework.

A `Preset` is a named, frozen, provenanced bundle of scenario assignments
(variable name to numeric value) plus variant selections. Presets are the
standard way to feed a calibrated scenario into the resolver. The framework
lives in core; concrete hardware, workload, and economic preset instances
live under `gpu_stack.presets.*`.

The framework intentionally refuses to invent numbers. Every Preset carries a
`source` string and a `notes` list for audit. A Preset with no source is
still legal for quick scratch use, but downstream code that wants auditable
numbers should reject them.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from types import MappingProxyType
from typing import Dict, Iterable, List, Mapping, Optional, Tuple

from .registry import Registry
from .resolver import (
    InvalidVariantSelector,
    ResolverError,
    ResolverResult,
    UnresolvedInput,
    _validate_variant_selectors,
    resolve,
)


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


@dataclass(frozen=True)
class Preset:
    """
    Named bundle of scenario assignments.

    Parameters
    ----------
    name
        Short identifier such as "h100_sxm_8gpu_node" or "chinchilla_dense".
    description
        One or two sentences explaining what the preset represents.
    assignments
        Mapping from registered variable name to numeric value. Values are
        plain floats or ints. Unit consistency is the caller's responsibility
        since the registry still has shallow unit coverage.
    variants
        Mapping from variable name to a variant key for multi-definition
        variables tagged with RelationRole.VARIANT. Example:
        {"training.flops_per_step": "dense"}.
    source
        Provenance string. Vendor datasheet, paper, internal memo, or note
        that the value is a rough assumption.
    notes
        Free-form notes: calibration caveats, applicability regimes,
        known imprecise entries.
    """

    name: str
    description: str
    assignments: Mapping[str, float] = field(default_factory=dict)
    variants: Mapping[str, str] = field(default_factory=dict)
    source: Optional[str] = None
    notes: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        assignments = dict(self.assignments)
        variants = dict(self.variants)
        notes = tuple(self.notes)

        # Catch typos in variable names early. A preset that references an
        # unknown variable name is almost always a mistake.
        unknown = [k for k in assignments if k not in Registry.variables]
        if unknown:
            raise ValueError(
                f"preset {self.name!r} references unknown variables: {sorted(unknown)}"
            )
        unknown_variants = [k for k in variants if k not in Registry.variables]
        if unknown_variants:
            raise ValueError(
                f"preset {self.name!r} selects variants for unknown variables: "
                f"{sorted(unknown_variants)}"
            )
        try:
            _validate_variant_selectors(variants)
        except InvalidVariantSelector as exc:
            raise ValueError(
                f"preset {self.name!r} has invalid variant selector: {exc}"
            ) from exc
        object.__setattr__(self, "assignments", MappingProxyType(assignments))
        object.__setattr__(self, "variants", MappingProxyType(variants))
        object.__setattr__(self, "notes", notes)

    def has_source(self) -> bool:
        """True when the preset carries non-blank provenance text."""
        return bool(self.source and self.source.strip())

    def require_source(self) -> "Preset":
        """
        Return this preset when it is sourced, otherwise raise.

        This keeps scratch presets legal while giving audit-sensitive callers
        a compact guard before resolving or combining calibrated scenarios.
        """
        if not self.has_source():
            raise ValueError(f"preset {self.name!r} has no source")
        return self

    def source_summary(self) -> Dict[str, object]:
        """Return a compact provenance snapshot for audit/reporting code."""
        return {
            "name": self.name,
            "has_source": self.has_source(),
            "source": self.source.strip() if self.has_source() else None,
            "assignment_count": len(self.assignments),
            "variant_count": len(self.variants),
            "note_count": len(self.notes),
        }

    def resolve(self, target: str) -> ResolverResult:
        """
        Evaluate `target` using this preset's assignments and variant
        selections. Thin wrapper around `core.resolver.resolve`.
        """
        return resolve(
            target,
            assignments=dict(self.assignments),
            variants=dict(self.variants),
        )

    def evaluate_targets(self, targets: Iterable[Tuple[str, object]]) -> ScenarioReport:
        """
        Evaluate labeled targets and return a deterministic scenario report.

        Resolver failures are captured per target so one bad target does not
        prevent callers from inspecting the rest of the scenario artifact.
        """
        target_reports = tuple(
            self._evaluate_target(label, target)
            for label, target in targets
        )
        issue_count = sum(report.issue_count for report in target_reports)
        status = "error" if any(r.status == "error" for r in target_reports) else (
            "issues" if issue_count else "ok"
        )
        return ScenarioReport(
            preset_name=self.name,
            preset_description=self.description,
            has_source=self.has_source(),
            source=self.source.strip() if self.has_source() else None,
            assignment_count=len(self.assignments),
            variant_count=len(self.variants),
            target_count=len(target_reports),
            status=status,
            issue_count=issue_count,
            targets=target_reports,
        )

    def _evaluate_target(self, label: str, target: object) -> ScenarioTargetReport:
        target_text = str(target)
        try:
            result = resolve(
                target,
                assignments=dict(self.assignments),
                variants=dict(self.variants),
            )
        except ResolverError as exc:
            unresolved_inputs = tuple(getattr(exc, "unresolved_inputs", ()) or ())
            missing_names = tuple(
                sorted(
                    item.variable for item in unresolved_inputs
                )
                or sorted(getattr(exc, "missing", set()) or ())
            )
            missing_count = len(missing_names)
            return ScenarioTargetReport(
                label=label,
                target=target_text,
                status="error",
                issue_count=1 + missing_count,
                missing_count=missing_count,
                missing_names=missing_names,
                unresolved_inputs=unresolved_inputs,
                missing_family_summaries=_missing_family_summaries(unresolved_inputs),
                error_type=type(exc).__name__,
                error_message=str(exc),
            )

        missing_names = tuple(sorted(result.missing))
        unresolved_inputs = tuple(
            sorted(result.unresolved_inputs, key=lambda item: item.variable)
        )
        violated_constraints = tuple(
            sorted(item.equation for item in result.violated_constraints)
        )
        violated_approximation_validity = tuple(
            sorted(
                check.equation
                for check in result.approximation_validity
                if check.satisfied is False
            )
        )
        issue_count = (
            len(missing_names)
            + len(violated_constraints)
            + len(violated_approximation_validity)
        )
        trace_equations = {step.equation for step in result.trace}
        trace_equation_names = tuple(sorted(trace_equations))
        return ScenarioTargetReport(
            label=label,
            target=target_text,
            status="issues" if issue_count else "ok",
            issue_count=issue_count,
            value=str(result.value),
            missing_count=len(missing_names),
            missing_names=missing_names,
            unresolved_inputs=unresolved_inputs,
            missing_family_summaries=_missing_family_summaries(unresolved_inputs),
            violated_constraint_count=len(violated_constraints),
            violated_constraint_equations=violated_constraints,
            violated_approximation_validity_count=len(violated_approximation_validity),
            violated_approximation_validity_equations=violated_approximation_validity,
            trace_step_count=len(result.trace),
            trace_equation_count=len(trace_equation_names),
            trace_equations=trace_equation_names,
        )

    def with_overrides(
        self,
        assignments: Optional[Mapping[str, float]] = None,
        variants: Optional[Mapping[str, str]] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        source: Optional[str] = None,
        notes: Optional[Iterable[str]] = None,
    ) -> "Preset":
        """Return a new Preset with the given fields overridden or merged."""
        merged_assignments: Dict[str, float] = dict(self.assignments)
        if assignments:
            merged_assignments.update(assignments)
        merged_variants: Dict[str, str] = dict(self.variants)
        if variants:
            merged_variants.update(variants)
        return Preset(
            name=name if name is not None else f"{self.name}+override",
            description=description if description is not None else self.description,
            assignments=merged_assignments,
            variants=merged_variants,
            source=source if source is not None else self.source,
            notes=tuple(notes) if notes is not None else self.notes,
        )


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


def combine(*presets: Preset, name: str, description: str = "") -> Preset:
    """
    Merge multiple presets into one. Later presets override earlier ones on
    key collisions. The combined preset records each component source.
    """
    if not presets:
        raise ValueError("combine() requires at least one preset")
    merged_assignments: Dict[str, float] = {}
    merged_variants: Dict[str, str] = {}
    sources: List[str] = []
    notes: List[str] = []
    for p in presets:
        merged_assignments.update(p.assignments)
        merged_variants.update(p.variants)
        if p.source:
            sources.append(f"{p.name}: {p.source}")
        notes.extend(p.notes)
    combined_source = " | ".join(sources) if sources else None
    return Preset(
        name=name,
        description=description or f"combined: {', '.join(p.name for p in presets)}",
        assignments=merged_assignments,
        variants=merged_variants,
        source=combined_source,
        notes=tuple(notes),
    )


__all__ = [
    "MissingFamilySummary",
    "ScenarioTargetReport",
    "ScenarioReport",
    "Preset",
    "combine",
]
