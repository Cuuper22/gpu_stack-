"""
core/presets.py
===============

The scenario-preset framework.

A `Preset` is a named, frozen bundle of scenario inputs: a mapping from
variable name to numeric value, plus variant selections for variables that
have more than one defining relation. It is the standard way to feed a
calibrated scenario into the resolver. This module holds the framework;
the concrete hardware, workload, and economic instances live under
`gpu_stack.presets.*`.

One rule shapes the design: never invent numbers silently. Every Preset
carries a `source` string and a `notes` tuple for audit. A Preset without a
source is still legal — scratch work needs that — but audit-sensitive
callers can demand provenance with `require_source()` and reject the rest.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Dict, Iterable, List, Mapping, Optional, Tuple

from .preset_provenance import (
    combined_source_for,
    has_source_text,
    normalized_source,
    preset_source_summary,
)
from .preset_reports import (
    MissingFamilySummary,
    ScenarioReport,
    ScenarioTargetReport,
    _missing_family_summaries,
)
from .registry import Registry
from .resolver import (
    InvalidVariantSelector,
    ResolverError,
    ResolverResult,
    _validate_variant_selectors,
    resolve,
)


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

        # A preset that references an unknown variable name is almost always
        # a typo; catch it at construction, not at resolve time.
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
        return has_source_text(self.source)

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
        return preset_source_summary(
            name=self.name,
            source=self.source,
            assignments=self.assignments,
            variants=self.variants,
            notes=self.notes,
        )

    def resolve(self, target: str) -> ResolverResult:
        """
        Evaluate `target` under this preset's assignments and variant
        selections. A thin wrapper around `core.resolver.resolve`.
        """
        return resolve(
            target,
            assignments=dict(self.assignments),
            variants=dict(self.variants),
        )

    def evaluate_targets(self, targets: Iterable[Tuple[str, object]]) -> ScenarioReport:
        """
        Evaluate labeled targets and return one deterministic ScenarioReport.

        Resolver failures are recorded per target rather than raised, so one
        bad target never hides the results for the rest of the scenario.
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
            source=normalized_source(self.source),
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


def combine(*presets: Preset, name: str, description: str = "") -> Preset:
    """
    Merge presets into one, later presets winning on key collisions.

    Notes concatenate, and the combined `source` lists every component's
    source so provenance survives the merge.
    """
    if not presets:
        raise ValueError("combine() requires at least one preset")
    merged_assignments: Dict[str, float] = {}
    merged_variants: Dict[str, str] = {}
    notes: List[str] = []
    for p in presets:
        merged_assignments.update(p.assignments)
        merged_variants.update(p.variants)
        notes.extend(p.notes)
    return Preset(
        name=name,
        description=description or f"combined: {', '.join(p.name for p in presets)}",
        assignments=merged_assignments,
        variants=merged_variants,
        source=combined_source_for(presets),
        notes=tuple(notes),
    )


__all__ = [
    "MissingFamilySummary",
    "ScenarioTargetReport",
    "ScenarioReport",
    "Preset",
    "combine",
]
