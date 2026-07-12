"""Adapter from the existing symbolic resolver to the research backend API."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping, Optional, Tuple

from ..core.presets import Preset
from ..core.registry import Registry
from ..core.resolver import ResolverError, resolve
from .backends import (
    BackendCapability,
    PredictionEstimate,
    PredictionRequest,
)


class SymbolicPredictionError(RuntimeError):
    """Raised when the symbolic graph cannot produce an honest numeric estimate."""


@dataclass(frozen=True)
class SymbolicResolverBackend:
    """Expose a :class:`Preset` and the registry resolver as a world-model backend."""

    preset: Optional[Preset] = None
    assignments: Mapping[str, float] = field(default_factory=dict)
    variants: Mapping[str, str] = field(default_factory=dict)
    name: str = "gpu_stack.symbolic"
    reject_violated_constraints: bool = True
    reject_violated_validity: bool = True

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("symbolic backend name must be non-blank")
        merged_assignments = dict(self.preset.assignments) if self.preset else {}
        merged_assignments.update(self.assignments)
        merged_variants = dict(self.preset.variants) if self.preset else {}
        merged_variants.update(self.variants)
        unknown = sorted(set(merged_assignments) - set(Registry.variables))
        if unknown:
            raise ValueError(f"symbolic backend assignments are unknown: {unknown}")
        object.__setattr__(
            self, "assignments", MappingProxyType(merged_assignments)
        )
        object.__setattr__(self, "variants", MappingProxyType(merged_variants))
        object.__setattr__(self, "name", self.name.strip())

    @property
    def capability(self) -> BackendCapability:
        return BackendCapability(
            targets=tuple(sorted(Registry.variables)),
            supports_temporal=False,
            supports_interventions=False,
            fidelity="symbolic-equation-graph",
        )

    def predict(self, request: PredictionRequest) -> PredictionEstimate:
        if request.intervention is not None or request.timestamp_s is not None:
            raise SymbolicPredictionError(
                "the static symbolic backend does not model temporal interventions"
            )
        assignments = dict(self.assignments)
        assignments.update(request.inputs)
        unknown = sorted(set(assignments) - set(Registry.variables))
        if unknown:
            raise SymbolicPredictionError(
                f"prediction inputs reference unknown variables: {unknown}"
            )
        try:
            result = resolve(
                request.target,
                assignments=assignments,
                variants=dict(self.variants),
            )
        except ResolverError as exc:
            raise SymbolicPredictionError(str(exc)) from exc

        if result.missing:
            raise SymbolicPredictionError(
                f"target {request.target!r} remains unresolved; missing "
                f"{sorted(result.missing)}"
            )
        violated_validity = tuple(
            check.equation
            for check in result.approximation_validity
            if check.satisfied is False
        )
        if self.reject_violated_constraints and result.violated_constraints:
            raise SymbolicPredictionError(
                "violated constraints: "
                + ", ".join(
                    sorted(item.equation for item in result.violated_constraints)
                )
            )
        if self.reject_violated_validity and violated_validity:
            raise SymbolicPredictionError(
                "violated approximation validity: "
                + ", ".join(sorted(violated_validity))
            )
        try:
            value = float(result.value)
        except (TypeError, ValueError) as exc:
            raise SymbolicPredictionError(
                f"target {request.target!r} produced non-numeric value {result.value!r}"
            ) from exc
        if not math.isfinite(value):
            raise SymbolicPredictionError(
                f"target {request.target!r} produced non-finite value {value!r}"
            )

        variable = Registry.variables[request.target]
        provenance: Tuple[str, ...] = ()
        if self.preset and self.preset.source:
            provenance = (self.preset.source.strip(),)
        assumptions = tuple(self.preset.notes) if self.preset else ()
        return PredictionEstimate(
            target=request.target,
            value=value,
            unit=str(variable.units),
            backend=self.name,
            assumptions=assumptions,
            provenance=provenance,
            diagnostics={
                "scenario_id": request.scenario_id,
                "trace_steps": len(result.trace),
                "trace_equations": tuple(step.equation for step in result.trace),
                "constraint_checks": len(result.constraints),
                "approximation_validity_checks": len(result.approximation_validity),
                "violated_constraints": tuple(
                    sorted(item.equation for item in result.violated_constraints)
                ),
                "violated_approximation_validity": tuple(
                    sorted(violated_validity)
                ),
            },
        )


__all__ = ["SymbolicPredictionError", "SymbolicResolverBackend"]
