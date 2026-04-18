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

from dataclasses import dataclass, field, replace
from typing import Dict, Iterable, List, Mapping, Optional, Tuple

from .registry import Registry
from .resolver import ResolverResult, resolve


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
        # Catch typos in variable names early. A preset that references an
        # unknown variable name is almost always a mistake.
        unknown = [k for k in self.assignments if k not in Registry.variables]
        if unknown:
            raise ValueError(
                f"preset {self.name!r} references unknown variables: {sorted(unknown)}"
            )
        unknown_variants = [k for k in self.variants if k not in Registry.variables]
        if unknown_variants:
            raise ValueError(
                f"preset {self.name!r} selects variants for unknown variables: "
                f"{sorted(unknown_variants)}"
            )

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


__all__ = ["Preset", "combine"]
